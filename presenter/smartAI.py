from __future__ import annotations
from typing import List, Any

from model.game import Game
from .ai import BaseController


class GeneralStrategus(BaseController):
    """
    STRATÉGIE :
    1. Crossbows focus les Pikemen puis autres crossbows
    2. Pikemen chassent activement les Knights
    3. Knights rush les Crossbows 
    """

    def __init__(self, team: str, decision_interval: float = 0.1):
        super().__init__(team, decision_interval)
        
    def decide_actions(self, game: Game) -> List[tuple[Any, ...]]:
        actions: List[tuple[Any, ...]] = []
        my_units = game.alive_units_of_team(self.team)
        enemies = game.enemy_units_of(self.team)
        
        if not my_units or not enemies:
            return actions
        
        # Séparer par type
        my_crossbows = [u for u in my_units if u.__class__.__name__ == "Crossbowman"]
        my_pikemen = [u for u in my_units if u.__class__.__name__ == "Pikeman"]
        my_knights = [u for u in my_units if u.__class__.__name__ == "Knight"]
        
        # Comportement optimisé par type
        for crossbow in my_crossbows:
            self._crossbow_behavior(crossbow, enemies, game)
        
        for pikeman in my_pikemen:
            self._pikeman_behavior(pikeman, enemies, game)
        
        for knight in my_knights:
            self._knight_behavior(knight, enemies, game)
            
        return actions

    def _crossbow_behavior(self, crossbow, enemies, game):
        """        
        PRIORITÉS (basées sur efficacité de kill) :
        1. Pikemen ennemis (8 dmg, tue en 7 coups) → BONUS +3
        2. Crossbows ennemis (5 dmg, tue en 7 coups) → Duel rangé
        3. Knights (4 dmg, tue en 25 coups) → Dernier recours
        """
        target = self._choose_crossbow_target(crossbow, enemies, game)
        
        if target is None:
            return
        
        dist = game.map.distance(crossbow, target)
        cb_range = float(getattr(crossbow, "range", 5.0))
        
        if dist <= cb_range:
            self._assign_intent(crossbow, ("attack", target), game)
        else:
            target_x = float(getattr(target, "x", 0.0))
            target_y = float(getattr(target, "y", 0.0))
            self._assign_intent(crossbow, ("move_to", target_x, target_y), game)
    
    def _choose_crossbow_target(self, crossbow, enemies, game):
        
        if not enemies:
            return None
        
        best_target = None
        best_score = -float("inf")
        
        for enemy in enemies:
            score = 0.0
            hp = float(getattr(enemy, "hp", 100))
            enemy_type = enemy.__class__.__name__
            dist = game.map.distance(crossbow, enemy)
            
            # PRIORITÉ 1 : Pikemen 
            if enemy_type == "Pikeman":
                score += 200
                
                if hp <= 16:  # 2 hits to kill
                    score += 150
                elif hp <= 24:  # 3 hits
                    score += 100
                elif hp <= 32:  # 4 hits
                    score += 50
            
            # PRIORITÉ 2 : Crossbows 
            elif enemy_type == "Crossbowman":
                score += 180
                # Finition rapide (fragiles, 35 HP)
                if hp <= 10:  # 2 hits
                    score += 120
                elif hp <= 15:  # 3 hits
                    score += 80
                elif hp <= 20:  # 4 hits
                    score += 40
            
            # PRIORITÉ 3 : Knights 
            elif enemy_type == "Knight":
                score += 50
                # Bonus si déjà très blessé
                if hp <= 20:  # Presque mort
                    score += 100
                elif hp <= 40:
                    score += 50
            
            # Bonus de proximité (important pour crossbow, range 5)
            if dist <= 5.0:  # À portée
                score += 80
            elif dist <= 8.0:
                score += 40
            elif dist <= 12.0:
                score += 20
            else:
                score -= 10  # Pénalité si trop loin
            
            if score > best_score:
                best_score = score
                best_target = enemy
        
        return best_target
    
    def _pikeman_behavior(self, pikeman, enemies, game):
        """
        Pikeman 
        PRIORITÉS :
        1. Knights (10 dmg, tue en 10 coups) 
        2. Autres cibles (4 dmg seulement)
        """
        target = self._choose_pikeman_target(pikeman, enemies, game)
        
        if target is None:
            return
        
        dist = game.map.distance(pikeman, target)
        pike_range = float(getattr(pikeman, "range", 1.0))
        
        if dist <= pike_range:
            self._assign_intent(pikeman, ("attack", target), game)
        else:
            target_x = float(getattr(target, "x", 0.0))
            target_y = float(getattr(target, "y", 0.0))
            self._assign_intent(pikeman, ("move_to", target_x, target_y), game)
    
    def _choose_pikeman_target(self, pikeman, enemies, game):
        """
        Pikeman = spécialiste anti-Knight
        """
        if not enemies:
            return None
        
        best_target = None
        best_score = -float("inf")
        
        for enemy in enemies:
            score = 0.0
            hp = float(getattr(enemy, "hp", 100))
            enemy_type = enemy.__class__.__name__
            dist = game.map.distance(pikeman, enemy)
            
            # PRIORITÉ ABSOLUE : Knights 
            if enemy_type == "Knight":
                score += 300  # Priorité maximale
                # Finition selon HP
                if hp <= 20:  # 2 hits
                    score += 150
                elif hp <= 40:  # 4 hits
                    score += 100
                elif hp <= 60:  # 6 hits
                    score += 60
            
            # PRIORITÉ 2 : Crossbows 
            elif enemy_type == "Crossbowman":
                score += 80
                if hp <= 12:  # 3 hits
                    score += 80
                elif hp <= 20:
                    score += 40
            
            # PRIORITÉ 3 : Pikemen 
            elif enemy_type == "Pikeman":
                score += 40
                if hp <= 16:  # 4 hits
                    score += 60
            
            # Bonus de proximité 
            if dist <= 1.0:  # À portée melee
                score += 100
            elif dist <= 3.0:
                score += 60
            elif dist <= 5.0:
                score += 30
            else:
                score += max(0, 20 - dist * 2)
            
            if score > best_score:
                best_score = score
                best_target = enemy
        
        return best_target
    
    def _knight_behavior(self, knight, enemies, game):
        """
        Knight 
        
        PRIORITÉS :
        1. Crossbows 
        2. Pikemen 
        3. Knights 
        """
        target = self._choose_knight_target(knight, enemies, game)
        
        if target is None:
            return
        
        dist = game.map.distance(knight, target)
        knight_range = float(getattr(knight, "range", 1.0))
        
        if dist <= knight_range:
            self._assign_intent(knight, ("attack", target), game)
        else:
            target_x = float(getattr(target, "x", 0.0))
            target_y = float(getattr(target, "y", 0.0))
            self._assign_intent(knight, ("move_to", target_x, target_y), game)
    
    def _choose_knight_target(self, knight, enemies, game):
        """
        Knight =  éviter pikemen si possible
        """
        if not enemies:
            return None
        
        best_target = None
        best_score = -float("inf")
        
        for enemy in enemies:
            score = 0.0
            hp = float(getattr(enemy, "hp", 100))
            enemy_type = enemy.__class__.__name__
            dist = game.map.distance(knight, enemy)
            
            # PRIORITÉ 1 : Crossbows 
            if enemy_type == "Crossbowman":
                score += 250
                if hp <= 16:  # 2 hits
                    score += 150
                elif hp <= 24:  # 3 hits
                    score += 100
            
            # PRIORITÉ 2 : Knights 
            elif enemy_type == "Knight":
                score += 80
                if hp <= 30:  # Presque mort
                    score += 100
                elif hp <= 50:
                    score += 50
            
            # PRIORITÉ 3 : Pikemen 
            elif enemy_type == "Pikeman":
                score += 30  # Bas score de base
                # Seulement si très blessé ou pas d'autre choix
                if hp <= 16:  # 2 hits, finition acceptable
                    score += 120
                elif hp <= 32:  # 4 hits
                    score += 60
                else:
                    score -= 30  # Pénalité si full HP
            
            # Bonus de proximité 
            if dist <= 1.0:  # À portée melee
                score += 100
            elif dist <= 4.0:
                score += 60
            elif dist <= 8.0:
                score += 30
            else:
                score += max(0, 20 - dist)
            
            if score > best_score:
                best_score = score
                best_target = enemy
        
        return best_target