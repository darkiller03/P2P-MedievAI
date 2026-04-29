from __future__ import annotations
from typing import List, Any

from model.game import Game


class BaseController:
    def __init__(self, team: str, decision_interval: float = 0.5):
        self.team = team
        self.decision_interval = float(decision_interval)

    def decide_actions(self, game: Game) -> List[tuple[Any, ...]]:
        raise NotImplementedError

    def _assign_intent(self, unit, intent, game: Game):
        """Assigne une intention si l'IA possède les droits (acteur + cible), sinon la met en attente et demande les droits."""
        local_id = game.local_player_id
        
        # 1. Vérifier la propriété de l'unité actrice
        if getattr(unit, "proprietaire_reseau", None) != local_id:
            # Option C — Réclamation Légitime :
            # Si c'est notre propre unité (même équipe) mais que l'adversaire en a le jeton,
            # on le réclame activement au lieu d'abandonner l'unité.
            if getattr(unit, "team", None) == local_id:
                if unit.uid not in game.pending_requests:
                    print(f"[{local_id}] ♟️ Réclamation de notre unité {unit.uid} "
                          f"(actuellement détenue par '{unit.proprietaire_reseau}'). Envoi req_own.")
            game.pending_actions[unit.uid] = intent
            game.request_ownership(unit.uid)
            return
            
        # 2. Pour un déplacement : le propriétaire de l'unité peut toujours la déplacer librement
        #    (pas besoin de propriété de case, c'est réservé à la construction)
        kind = intent[0]
        if kind == "attack":
            _, target = intent
            # Pour attaquer : on doit aussi posséder la cible (pour modifier ses HP)
            if getattr(target, "proprietaire_reseau", None) != local_id:
                game.pending_actions[unit.uid] = intent
                game.request_ownership(target.uid)
                return
                
        # Si on possède tout ce qu'il faut, on assigne l'action immédiatement !
        unit.intent = intent


class CaptainBraindead(BaseController):
    """
    Captain BRAINDEAD - Attaque uniquement les ennemis visibles, ne se déplace pas.
    """

    def __init__(self, team: str, decision_interval: float = 0.7):
        super().__init__(team, decision_interval)

    def decide_actions(self, game: Game) -> List[tuple[Any, ...]]:
        actions: List[tuple[Any, ...]] = []
        my_units = game.alive_units_of_team(self.team)
        enemies = game.enemy_units_of(self.team)

        for u in my_units:
            if not enemies:
                continue

            best_target = None
            best_dist = float("inf")

            los = float(getattr(u, "lineOfSight", 0.0))

            # On ne considère que les ennemis dans la line of sight
            for e in enemies:
                dist = game.map.distance(u, e)
                if dist <= los and dist < best_dist:
                    best_dist = dist
                    best_target = e

            if best_target is None:
                continue

            if hasattr(u, "in_range") and u.in_range(best_dist):
                self._assign_intent(u, ("attack", best_target), game)

        return actions


class MajorDaft(BaseController):
    """
    Major DAFT - Attaque agressivement l'ennemi le plus proche.
    """

    def __init__(self, team: str, decision_interval: float = 0.3):
        super().__init__(team, decision_interval)


    def decide_actions(self, game: Game) -> List[tuple[Any, ...]]:
        actions: List[tuple[Any, ...]] = []
        my_units = game.alive_units_of_team(self.team)

        for u in my_units:
            target = game.find_closest_enemy(u)
            if target is None:
                continue

            dist = game.map.distance(u, target)

            if hasattr(u, "in_range") and u.in_range(dist):
                self._assign_intent(u, ("attack", target), game)
                continue

            target_x = float(getattr(target, "x", 0.0))
            target_y = float(getattr(target, "y", 0.0))
            self._assign_intent(u, ("move_to", target_x, target_y), game)

        return actions


class AssasinJack(BaseController):
    """
    Assasin Jack - Cible en priorité les ennemis faibles et blessés.
    """

    def __init__(self, team: str, decision_interval: float = 0.3):
        super().__init__(team, decision_interval)


    def decide_actions(self, game: Game) -> List[tuple[Any, ...]]:
        actions: List[tuple[Any, ...]] = []
        my_units = game.alive_units_of_team(self.team)

        for u in my_units:
            enemies = game.enemy_units_of(self.team)
            if not enemies:
                continue

            target = None
            best_score = float("inf")
            MAX_CHASE_DIST = 15.0
            closest_enemy = None
            closest_dist = float("inf")

            for e in enemies:
                d = game.map.distance(u, e)
                hp = float(getattr(e, "hp", 100))

                if d < closest_dist:
                    closest_dist = d
                    closest_enemy = e

                if d < MAX_CHASE_DIST:
                    if hp < best_score:
                        best_score = hp
                        target = e

            if target is None:
                target = closest_enemy

            if target is None:
                continue

            dist = game.map.distance(u, target)

            if hasattr(u, "in_range") and u.in_range(dist):
                self._assign_intent(u, ("attack", target), game)
                continue

            target_x = float(getattr(target, "x", 0.0))
            target_y = float(getattr(target, "y", 0.0))
            self._assign_intent(u, ("move_to", target_x, target_y), game)

        return actions

class PredictEinstein(BaseController):
    """
    Predict Einstein - IA avancée avec focus fire, counter-types et ciblage intelligent.
    """

    def __init__(self, team: str, decision_interval: float = 0.15):
        super().__init__(team, decision_interval)
        self._focus_targets: dict = {}
        self._last_tick = -1
        self._cached_enemy_hp: dict = {}

    def _get_unit_type_name(self, unit) -> str:
        """Retourne le nom du type d'unité."""
        return type(unit).__name__

    def _get_counter_bonus(self, attacker, target) -> float:
        attacker_type = self._get_unit_type_name(attacker)
        target_type = self._get_unit_type_name(target)

        if attacker_type == "Pikeman" and target_type == "Knight":
            return 3.0
        if attacker_type == "Crossbowman" and target_type == "Pikeman":
            return 2.0
        if attacker_type == "Knight" and target_type == "Crossbowman":
            return 2.5
        return 1.0

    def _estimate_accuracy(self, unit) -> float:
        """Retourne la précision estimée (0.0 à 1.0)."""
        acc = getattr(unit, "accuracy", 100)
        return float(acc) / 100.0

    def _quick_kill_estimate(self, unit, enemy) -> tuple:
        accuracy = self._estimate_accuracy(unit)
        damage_per_hit = unit.calculer_degats(enemy, 1.0) * accuracy

        if damage_per_hit <= 0:
            return (999, False)

        hits_needed = enemy.hp / damage_per_hit
        can_kill_fast = hits_needed <= 3

        return (hits_needed, can_kill_fast)

    def _calculate_fast_score(self, unit, enemy, dist, focus_counts: dict) -> float:
        hits_needed, can_kill_fast = self._quick_kill_estimate(unit, enemy)

        if can_kill_fast:
            base_score = hits_needed * 2 + dist * 0.3
        else:
            base_score = hits_needed + dist * 0.5

        hp_ratio = enemy.hp / getattr(enemy, "max_hp", enemy.hp)
        if hp_ratio < 0.3:
            base_score *= 0.3
        elif hp_ratio < 0.5:
            base_score *= 0.5
        elif hp_ratio < 0.7:
            base_score *= 0.7

        counter_bonus = self._get_counter_bonus(unit, enemy)
        base_score /= counter_bonus

        enemy_id = id(enemy)
        current_focus = focus_counts.get(enemy_id, 0)

        if can_kill_fast and current_focus > 0 and current_focus < 5:
            base_score *= 0.8
        elif current_focus >= 5:
            base_score *= 1.3

        reach = unit.range if unit.range > 0 else 1.0
        if dist <= reach:
            base_score *= 0.6

        return base_score

    def decide_actions(self, game: Game) -> List[tuple[Any, ...]]:
        actions: List[tuple[Any, ...]] = []
        my_units = game.alive_units_of_team(self.team)

        if not my_units:
            return actions

        current_tick = getattr(game, "time", 0)
        if current_tick != self._last_tick:
            self._focus_targets = {}
            self._last_tick = current_tick

        enemies = game.enemy_units_of(self.team)
        if not enemies:
            return actions

        alive_enemies = [e for e in enemies if e.est_vivant()]
        if not alive_enemies:
            return actions

        focus_counts: dict = {}
        unit_assignments: list = []

        for u in my_units:
            if not u.est_vivant():
                continue

            best_target = None
            best_score = float("inf")
            best_dist = float("inf")
            max_consider_range = 25.0

            candidates = []
            for e in alive_enemies:
                dist = game.map.distance(u, e)
                if dist <= max_consider_range:
                    candidates.append((e, dist))

            if not candidates:
                closest = None
                closest_dist = float("inf")
                for e in alive_enemies:
                    dist = game.map.distance(u, e)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest = e
                if closest:
                    candidates = [(closest, closest_dist)]

            for e, dist in candidates:
                score = self._calculate_fast_score(u, e, dist, focus_counts)

                if score < best_score:
                    best_score = score
                    best_target = e
                    best_dist = dist

            if best_target:
                unit_assignments.append((u, best_target, best_dist))
                enemy_id = id(best_target)
                focus_counts[enemy_id] = focus_counts.get(enemy_id, 0) + 1

        for u, target, dist in unit_assignments:
            reach = u.range if u.range > 0 else 1.0
            if dist <= reach:
                self._assign_intent(u, ("attack", target), game)
            else:
                target_x = float(getattr(target, "x", 0.0))
                target_y = float(getattr(target, "y", 0.0))
                self._assign_intent(u, ("move_to", target_x, target_y), game)

        return actions

class SimpleAI(MajorDaft):
    pass
