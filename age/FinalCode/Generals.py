from __future__ import annotations
from dataclasses import dataclass
import random
import math

@dataclass
class General:
    def __init__(self, player: int):
        self.player = player
    def give_orders(self, engine: SimpleEngine):
        raise NotImplementedError

class BrainDeadGeneral(General):
    def give_orders(self, engine: SimpleEngine):
        my_units = engine.get_units_for_player(self.player)
        for u in my_units:
            if u.target_id is not None and u.target_id in engine.units_by_id:
                continue
            enemies = [e for e in engine.units if e.player != self.player and e.alive]
            if not enemies:
                return
            nearby = [e for e in enemies if u.distance_to(e) < 5.0]
            if nearby:
                target = min(nearby, key=lambda e: u.distance_to(e))
                u.target_id = target.id

class DaftGeneral(General):
    def give_orders(self, engine: SimpleEngine):
        my_units = engine.get_units_for_player(self.player)
        enemy_units = [u for u in engine.units if u.player != self.player and u.alive]
        if not enemy_units:
            return
        for u in my_units:
            if u.target_id is not None and u.target_id in engine.units_by_id:
                continue
            nearest = min(enemy_units, key=lambda e: u.distance_to(e))
            u.target_id = nearest.id
class New_General_1(General):
    def __init__(self, player: int):
        super().__init__(player)
        self.last_update = 0.0
        self.update_interval = 0.3  # seconds between decision updates

    def give_orders(self, engine: "SimpleEngine"):
        t = engine.tick
        if t - self.last_update < self.update_interval:
            return  # avoid changing targets every frame
        self.last_update = t

        my_units = engine.get_units_for_player(self.player)
        enemies = [u for u in engine.units if u.player != self.player and u.alive]

        if not enemies:
            return

        # map: enemy_id -> number of allies already targeting
        focus_count = {}
        for u in my_units:
            if u.target_id in focus_count:
                focus_count[u.target_id] += 1
            elif u.target_id is not None:
                focus_count[u.target_id] = 1

        for u in my_units:
            # --- Monks: heal first ---
            if u.unit_type == "Monk":
                self.handle_monk(u, engine)
                continue

            # Skip if already attacking alive target
            if u.target_id is not None and u.target_id in engine.units_by_id and engine.units_by_id[u.target_id].alive:
                continue

            # Choose best target
            best_enemy = self.choose_best_target(u, enemies, focus_count)
            if best_enemy:
                u.target_id = best_enemy.id

    # --------------------------
    # Monk behavior
    # --------------------------
    def handle_monk(self, monk: "Unit", engine: "SimpleEngine"):
        allies = [a for a in engine.units if a.player == monk.player and a.hp < 55 and a.alive]
        if not allies:
            return  # nothing to heal

        # Prioritize lowest HP ally
        target = min(allies, key=lambda a: a.hp)
        dist = monk.distance_to(target)
        dt = 0.2  # assume small timestep for healing scale

        if dist <= monk.range:
            target.hp = min(target.hp + monk.attack * dt * 2, 55)
        else:
            # move closer
            dx = target.x - monk.x
            dy = target.y - monk.y
            dist = max(math.hypot(dx, dy), 1e-6)
            monk.x += dx / dist * monk.speed * dt
            monk.y += dy / dist * monk.speed * dt

    # --------------------------
    # Target selection with focus fire & kiting
    # --------------------------
    def choose_best_target(self, u: "Unit", enemies: list, focus_count: dict):
        best_score = -9999
        best_enemy = None

        for e in enemies:
            dist = u.distance_to(e)
            score = 0

            # --- Unit-specific priorities ---
            if u.unit_type == "Pikeman":
                if e.unit_type == "knight": score += 50
                if e.unit_type == "Crossbowman": score -= 10

            elif u.unit_type == "knight":
                if e.unit_type in ["Crossbowman", "mage"]: score += 60
                if e.unit_type == "Monk": score += 25
                if e.unit_type == "Pikeman": score -= 40

            elif u.unit_type == "Crossbowman":
                # prefer high value targets
                if e.unit_type in ["mage", "Crossbowman"]: score += 40
                if e.unit_type == "Monk": score += 30
                if e.unit_type == "knight": score -= 10
                # maintain distance from melee
                if dist < 2 and e.unit_type in ["Pikeman", "knight"]:
                    score -= 30

            elif u.unit_type == "mage":
                if e.unit_type in ["Crossbowman", "mage"]: score += 40
                if e.unit_type == "knight": score += 20
                if e.unit_type == "Pikeman": score -= 15

            # --- Generic scoring ---
            score -= dist  # prefer closer
            score += (10 - e.hp * 0.1)  # finish weak units

            # --- Focus fire bonus ---
            if e.id in focus_count:
                score += focus_count[e.id] * 5

            if score > best_score:
                best_score = score
                best_enemy = e

        return best_enemy


class New_General_2(General):
    def __init__(self, player: int):
        super().__init__(player)
        self.last_update = 0.0
        self.update_interval = 0.25  # responsive but stable
        self.kite_step_dt = 0.18     # micro-step amount for kiting/retreat
        self.rally_point = None      # computed each update (x,y)

    def handle_monk(self, unit, engine, enemies):
        # simple safe monk behavior: heal lowest hp ally but avoid suicide
        allies = [a for a in engine.units if a.player == unit.player and a.alive and a.hp < 55]
        if not allies:
            return
        # prefer protected allies (behind friends) but prioritize lowest HP
        target = min(allies, key=lambda a: a.hp)
        dist = unit.distance_to(target)
        # if melee threats too close, avoid going directly into danger: move toward rally point instead
        threats = [e for e in enemies if e.alive and unit.distance_to(e) <= 3.0 and e.unit_type.lower() in ("knight", "pikeman")]
        if threats:
            # stay back toward rally point
            if self.rally_point:
                self.retreat_to_point(unit, self.rally_point, dt=self.kite_step_dt)
            return

        # heal if in range, else move toward ally (full speed)
        if dist <= unit.range:
            heal_amount = unit.attack * self.update_interval * 2  # consistent with Unit.step healing (approx)
            target.hp = min(target.hp + heal_amount, 55)
        else:
            dx = target.x - unit.x
            dy = target.y - unit.y
            d = math.hypot(dx, dy)
            if d > 1e-6:
                nx = dx / d
                ny = dy / d
                step_len = unit.speed * self.kite_step_dt
                unit.x += nx * step_len
                unit.y += ny * step_len

    def give_orders(self, engine: "SimpleEngine"):
        t = engine.tick
        if t - self.last_update < self.update_interval:
            return
        self.last_update = t

        my_units = engine.get_units_for_player(self.player)
        enemies = [u for u in engine.units if u.player != self.player and u.alive]

        # If no enemies remain, do nothing (prevents empty-list errors)
        if not enemies:
            return

        if not my_units:
            return

        # compute rally point = center of mass of friendly units
        self.rally_point = self.compute_army_center(my_units)

        # map: enemy_id -> number of allies already targeting
        focus_count: Dict[int,int] = {}
        for u in my_units:
            if u.target_id is not None:
                focus_count[u.target_id] = focus_count.get(u.target_id, 0) + 1

        # main per-unit decision loop
        for u in my_units:
            # if this unit already has a target and that target is alive:
            if u.target_id is not None:
                tgt = engine.units_by_id.get(u.target_id)
                if tgt and tgt.alive:
                    dist = u.distance_to(tgt)
                    # If in attack range -> keep target and do nothing (ensures an attack tick)
                    if dist <= u.range * 1.05:
                        continue
                    # If slightly out of range (close), do nothing here and let Unit.step() micro-approach
                    # to keep full-speed following when far, and precise micro-approach when near.
                    # (We avoid issuing movement commands that would cancel an upcoming attack.)
                else:
                    # stale/invalid target -> clear
                    u.target_id = None

            # monks: healer logic
            if u.unit_type.lower() == "monk":
                self.handle_monk(u, engine, enemies)
                continue

            # evaluate local situation (friends vs foes near this unit)
            friends_near, foes_near = self.evaluate_local_battle(u, engine, radius=6.0)

            # RETREAT logic: if outnumbered badly or low hp -> fall back to rally point,
            # but if can land one attack this tick, do it first.
            if (foes_near > friends_near * 1.2) or (u.hp < 20 and foes_near > 0):
                if u.target_id is not None:
                    tgt = engine.units_by_id.get(u.target_id)
                    if tgt and tgt.alive and u.distance_to(tgt) <= u.range * 1.05:
                        # attack this tick, then retreat on next decision tick
                        continue
                # otherwise retreat now
                self.retreat_to_point(u, self.rally_point, dt=self.kite_step_dt)
                u.target_id = None
                continue

            # Knight special: try to dive backline when safe
            if u.unit_type.lower() == "knight":
                target = self.pick_backline_target_for_knight(u, enemies, focus_count, engine)
                if target:
                    u.target_id = target.id
                    continue

            # Pikeman special: intercept knights if nearby
            if u.unit_type.lower() == "pikeman":
                knight = self.find_nearest_enemy_of_type(u, enemies, "knight", max_dist=8.0)
                if knight:
                    u.target_id = knight.id
                    continue

            # Ranged micro: if melee threat is near, micro-step away this tick (kiting)
            if u.unit_type.lower() in ("crossbowman", "mage"):
                melee = self.find_nearest_enemy_of_types(u, enemies, ["pikeman", "knight"], max_dist=5.0)
                if melee:
                    dist = u.distance_to(melee)
                    if dist < max(2.0, u.range * 0.7):
                        # micro-step away a bit (don't clear target)
                        self.micro_step_away(u, melee, dt=self.kite_step_dt)
                        continue

            # Skip changing targets if already attacking a live target (we handled in-range above)
            if u.target_id is not None and u.target_id in engine.units_by_id and engine.units_by_id[u.target_id].alive:
                continue

            # Choose best target normally (focus + counters)
            best_enemy = self.choose_best_target(u, enemies, focus_count)
            if best_enemy:
                u.target_id = best_enemy.id

    # --------------------------
    # Helpers
    # --------------------------
    def compute_army_center(self, units: List["Unit"]):
        if not units:
            return (0.0, 0.0)
        sx = sum(u.x for u in units)
        sy = sum(u.y for u in units)
        return (sx / len(units), sy / len(units))

    def evaluate_local_battle(self, unit: "Unit", engine: "SimpleEngine", radius: float = 6.0):
        friends = [u for u in engine.units if u.player == unit.player and u.alive and unit.distance_to(u) <= radius]
        foes = [u for u in engine.units if u.player != unit.player and u.alive and unit.distance_to(u) <= radius]
        return len(friends), len(foes)

    def retreat_to_point(self, unit: "Unit", point: tuple, dt: float = 0.18):
        px, py = point
        dx = px - unit.x
        dy = py - unit.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return
        nx = dx / dist
        ny = dy / dist
        # move toward rally point (retreat/regroup) using micro step
        step_len = unit.speed * dt
        unit.x += nx * step_len
        unit.y += ny * step_len

    def micro_step_away(self, unit: "Unit", threat: "Unit", dt: float = 0.18):
        # move directly away from threat a little bit (simple kite/micro)
        dx = unit.x - threat.x
        dy = unit.y - threat.y
        dist = max(math.hypot(dx, dy), 1e-6)
        nx = dx / dist
        ny = dy / dist
        step_len = unit.speed * dt
        unit.x += nx * step_len
        unit.y += ny * step_len

    def find_nearest_enemy_of_type(self, u: "Unit", enemies: List["Unit"], typ: str, max_dist: float = 9999.0):
        typ = typ.lower()
        candidates = [e for e in enemies if e.unit_type.lower() == typ]
        if not candidates:
            return None
        candidates = sorted(candidates, key=lambda e: u.distance_to(e))
        if candidates and u.distance_to(candidates[0]) <= max_dist:
            return candidates[0]
        return None

    def find_nearest_enemy_of_types(self, u: "Unit", enemies: List["Unit"], typlist: List[str], max_dist: float = 9999.0):
        typs = set([t.lower() for t in typlist])
        candidates = [e for e in enemies if e.unit_type.lower() in typs]
        if not candidates:
            return None
        candidates = sorted(candidates, key=lambda e: u.distance_to(e))
        if candidates and u.distance_to(candidates[0]) <= max_dist:
            return candidates[0]
        return None

    def pick_backline_target_for_knight(self, u: "Unit", enemies: List["Unit"], focus_count: Dict[int,int], engine: "SimpleEngine"):
        # guard: if no enemies, nothing to pick
        if not enemies:
            return None
        # prefer fragile ranged units (mage/crossbowman) that are not heavily protected by friends
        candidates = [e for e in enemies if e.unit_type.lower() in ("crossbowman", "mage")]
        if not candidates:
            # fallback: nearest enemy (safe because enemies is non-empty here)
            return min(enemies, key=lambda e: u.distance_to(e))
        # score them, but prefer those with fewer defenders nearby
        best = None
        best_score = -9e9
        for e in candidates:
            dist = u.distance_to(e)
            # count defenders near the candidate
            defenders = sum(1 for a in engine.units if a.player == e.player and a.alive and e.distance_to(a) <= 4.0)
            score = -dist - defenders * 6  # farther & more defenders = worse
            # prefer low-HP targets
            score += (10 - e.hp * 0.1)
            # small bonus if already focused (so knight can finish)
            score += focus_count.get(e.id, 0) * 3
            if score > best_score:
                best_score = score
                best = e
        return best

    # --------------------------
    # Target selection (scoring)
    # --------------------------
    def choose_best_target(self, u: "Unit", enemies: List["Unit"], focus_count: Dict[int,int]):
        # safety: if no enemies available, return None
        if not enemies:
            return None

        best_score = -9e9
        best_enemy = None
        ut = u.unit_type.lower()

        for e in enemies:
            e_ut = e.unit_type.lower()
            dist = u.distance_to(e)
            score = 0.0

            # unit-specific counters / priorities
            if ut == "pikeman":
                if e_ut == "knight": score += 70
                if e_ut == "mage": score += 5
                if e_ut == "crossbowman": score -= 8

            elif ut == "knight":
                if e_ut in ("crossbowman", "mage"): score += 80
                if e_ut == "monk": score += 30
                if e_ut == "pikeman": score -= 50

            elif ut == "crossbowman":
                if e_ut in ("mage", "crossbowman"): score += 40
                if e_ut == "monk": score += 30
                if e_ut == "knight": score -= 12
                # penalize being too close to melee
                if dist < 2.0 and e_ut in ("pikeman", "knight"):
                    score -= 35

            elif ut == "mage":
                # mage behaves like ranged single-target for now (no AOE)
                if e_ut in ("crossbowman", "mage"): score += 45
                if e_ut == "knight": score += 15
                if e_ut == "pikeman": score -= 12

            # generic scoring: prefer closer and lower hp
            score -= dist * 0.9
            score += (10.0 - e.hp * 0.1)

            # focus-fire: if many allies already on this enemy, join them
            score += focus_count.get(e.id, 0) * 6

            # small randomness to break ties and make behavior varied
            score += random.uniform(-0.5, 0.5)

            # prefer targets within reasonable engagement range
            # if target is much farther than unit range, deprioritize slightly
            if dist > max(6.0, u.range * 3.0):
                score -= 8.0

            # prefer enemies that are not heavily defended
            defenders = sum(1 for a in enemies if a.player == e.player and a.alive and e.distance_to(a) <= 3.0)
            score -= defenders * 2.0

            if score > best_score:
                best_score = score
                best_enemy = e

        return best_enemy

class New_General_3(General):
    def __init__(self, player: int):
        super().__init__(player)
        self.global_targets = {}   # unit_type -> enemy_id
        self.retarget_cooldown = 0.0

    def give_orders(self, engine: "SimpleEngine"):
        t = engine.tick
        if t < self.retarget_cooldown:
            return

        my_units = engine.get_units_for_player(self.player)
        enemies = [u for u in engine.units if u.player != self.player and u.alive]
        if not enemies:
            return

        # clear dead targets
        for k, eid in list(self.global_targets.items()):
            if eid not in engine.units_by_id or not engine.units_by_id[eid].alive:
                del self.global_targets[k]

        # assign new global targets if missing
        for ut in {"pikeman", "knight", "crossbowman", "mage"}:
            if ut not in self.global_targets:
                tgt = self.pick_global_target(ut, enemies, engine)
                if tgt:
                    self.global_targets[ut] = tgt.id

        # enforce orders
        for u in my_units:
            ut = u.unit_type.lower()

            # monks stay healers (do not fight)
            if ut == "monk":
                continue

            # HARD LOCK: do not retarget individually
            if ut in self.global_targets:
                u.target_id = self.global_targets[ut]

        # retarget only after a kill wave
        self.retarget_cooldown = t + 1.5

    def pick_global_target(self, ut, enemies, engine):
        best = None
        best_score = -9e9

        for e in enemies:
            dist = 0  # distance is IRRELEVANT at this level
            score = 0

            # priority = damage removed per second
            if e.unit_type.lower() in ("crossbowman", "mage"):
                score += 120
            if e.unit_type.lower() == "knight":
                score += 80
            if e.unit_type.lower() == "pikeman":
                score += 50
            if e.unit_type.lower() == "monk":
                score += 100

            # favor already-engaged clusters
            nearby_allies = sum(
                1 for a in engine.units
                if a.player == self.player and a.alive and e.distance_to(a) < 3.5
            )
            score += nearby_allies * 5

            # fragile targets die faster → tempo advantage
            score += (60 - e.hp)

            if score > best_score:
                best_score = score
                best = e

        return best

class GenghisKhanPrimeGeneral(General):
    def give_orders(self, engine: "SimpleEngine"):
        my_units = engine.get_units_for_player(self.player)
        enemies = [u for u in engine.units if u.player != self.player and u.alive]
        
        if not enemies or not my_units:
            return

        # --- CONDITION DE SACRIFICE (improved) ---
        # Activate Finish-Him if:
        # 1. There are 15 enemies or less
        # 2. Or Braindead-style rush (more enemies than us early)
        advantage_ratio = len(my_units) / max(1, len(enemies))
        finish_him = len(enemies) <= 15 or advantage_ratio >= 1.0

        # Listes de menaces
        pikes = [e for e in enemies if e.unit_type == "Pikeman"]
        knights = [e for e in enemies if e.unit_type == "knight"]
        
        for u in my_units:
            u_type = u.unit_type

            # --- 1. ARBALÉTRIERS ---
            if u_type == "Crossbowman":
                # En mode FINISH HIM, on ne fuit plus du tout, on tire juste.
                if not finish_him:
                    nearest_threat = self.get_nearest(u, knights + pikes)
                    if nearest_threat:
                        dist = u.distance_to(nearest_threat)
                        if dist < 3.5:
                            # Stutter Step : On ne fuit que si on recharge
                            if u.reload_timer > 0:
                                self.move_away(u, nearest_threat, intensity=1.5)
                                u.target_id = None
                                continue

            # --- 2. CHEVALIERS ---
            if u_type == "knight":
                # En mode FINISH HIM, on ignore la peur des piquiers.
                if not finish_him:
                    nearest_pike = self.get_nearest(u, pikes)
                    if nearest_pike and u.distance_to(nearest_pike) < 2.5:
                        self.move_away(u, nearest_pike, intensity=2.0)
                        u.target_id = None
                        continue

            # --- 3. MOINES ---
            if u_type == "Monk":
                # Les moines restent prudents même à la fin (ils ne servent à rien au corps à corps)
                threat = self.get_nearest(u, enemies)
                if threat and u.distance_to(threat) < 2.5:
                    self.move_away(u, threat, intensity=1.0)
                    u.target_id = None
                    continue
                # Soin
                allies_hurt = [a for a in my_units if a.hp < a.max_hp]
                if allies_hurt:
                    u.target_id = min(allies_hurt, key=lambda a: a.hp).id
                continue

            # --- 4. CHOIX DE CIBLE ---
            # Optimisation : Si on a une cible valide à portée, on la garde
            # Sauf en mode Finish Him où on veut être sûr de taper le plus proche
            if not finish_him and u.target_id and u.target_id in engine.units_by_id:
                curr = engine.units_by_id[u.target_id]
                if curr.alive and u.distance_to(curr) <= u.range:
                    continue

            # On passe le flag finish_him à la fonction de ciblage
            best = self.choose_target(u, enemies, finish_him)
            if best:
                u.target_id = best.id

    def choose_target(self, u, enemies, finish_him):
        best_score = -9999
        best_target = None
        u_type = u.unit_type

        for e in enemies:
            dist = u.distance_to(e)
            
            # En mode FINISH HIM, la distance est le seul critère important
            if finish_him:
                score = -dist * 10
            else:
                score = -dist * 3 
                if e.hp < 10: score += 50
            
            e_type = e.unit_type

            # --- LOGIQUE DE CONTRE (Désactivée en Finish Him) ---
            if not finish_him:
                if u_type == "Pikeman":
                    if e_type == "knight": score += 200
                    elif e_type == "Pikeman": score += 10
                    
                elif u_type == "knight":
                    if e_type in ["Crossbowman", "Monk", "mage"]: score += 150
                    # On évite le piquier SEULEMENT si on n'est pas en train de finir la game
                    elif e_type == "Pikeman": score -= 500

                elif u_type == "Crossbowman":
                    if e_type == "Pikeman": score += 20 
                    if e_type == "knight": score += 30
                    if e_type == "Monk": score += 60
            
            # En mode Finish Him, on ajoute juste un petit bonus pour taper ce qu'on tape bien
            # Mais sans pénalité négative massive qui empêcherait d'attaquer
            else:
                if u_type == "Pikeman" and e_type == "knight": score += 50

            if score > best_score:
                best_score = score
                best_target = e
        
        return best_target

    def get_nearest(self, u, collection):
        if not collection: return None
        return min(collection, key=lambda x: u.distance_to(x))

    def move_away(self, u, threat, intensity=1.0):
        dx = u.x - threat.x
        dy = u.y - threat.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            u.x += (dx/dist) * u.speed * 0.2 * intensity
            u.y += (dy/dist) * u.speed * 0.2 * intensity







