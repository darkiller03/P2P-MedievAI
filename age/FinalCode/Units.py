from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import math

@dataclass
class Unit:
    id: int
    player: int
    x: float
    y: float
    hp: float = 0.0
    max_hp: Optional[float] = None
    attack: float = 50.0
    armor: float = 0.0
    range: float = 1.0
    speed: float = 1.0
    alive: bool = True
    target_id: Optional[int] = None
    regen: float = 0.
    reload_time: float = 1.0
    reload_timer: float = 0.0
    unit_type: str = "Pikeman"
    color: Optional[Tuple[int,int,int]] = None
    tags: List[str] = field(default_factory=list)
    bonuses: Dict[str, float] = field(default_factory=dict)
    
    # Paramètre de collision (Rayon de l'unité)
    radius: float = 0.4 

    def __post_init__(self):
        type_colors = {
            "Pikeman": (200, 50, 50),
            "Crossbowman": (255, 200, 50),
            "knight": (180, 180, 180),
            "mage": (120, 50, 200),
            "Monk": (50, 200, 120)
        }
        if self.color is None:
            self.color = type_colors.get(self.unit_type, (255, 255, 255))

        if self.max_hp is None:
            self.max_hp = self.hp

    def distance_to(self, other: "Unit") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def handle_collisions(self, engine: "SimpleEngine"):
        """Empêche les unités de se chevaucher (Algorithme de séparation)."""
        for other in engine.units:
            if other.id == self.id or not other.alive:
                continue
            
            dx = self.x - other.x
            dy = self.y - other.y
            dist = math.hypot(dx, dy)
            min_dist = self.radius + other.radius

            if dist < min_dist and dist > 0:
                overlap = min_dist - dist
                # On repousse l'unité de la moitié de l'interpénétration
                self.x += (dx / dist) * overlap * 0.5
                self.y += (dy / dist) * overlap * 0.5

    def step(self, dt: float, engine: "SimpleEngine"):
        if not self.alive:
            return

        # 1. Gestion des collisions
        self.handle_collisions(engine)

        # 2. Gestion du rechargement et régénération
        if self.reload_timer > 0:
            self.reload_timer -= dt

        if self.regen > 0:
            self.hp = min(self.hp + self.regen * dt, self.max_hp)

        # 3. Logique spécifique au Moine (Heal)
        if self.unit_type == "Monk":
            allies = [a for a in engine.units if a.player == self.player and a.alive and a.hp < a.max_hp]
            if allies:
                target = min(allies, key=lambda a: self.distance_to(a))
                dist = self.distance_to(target)
                if dist <= self.range:
                    if self.reload_timer <= 0:
                        target.hp = min(target.hp + self.regen, target.max_hp)
                        self.reload_timer = self.reload_time
                else:
                    self.move_towards(target, dt)
            return

        # 4. Logique de combat normale
        target = engine.units_by_id.get(self.target_id) if self.target_id is not None else None

        if target is None or not target.alive:
            self.target_id = None
            return

        d = self.distance_to(target)
        if d <= self.range + 0.2: # Marge pour les unités au corps à corps
            if self.reload_timer <= 0:
                # FORMULE AOE2 : Max(1, Somme des dégâts - Armure)
                total_attack = self.attack
                for tag in target.tags:
                    total_attack += self.bonuses.get(tag, 0.0)
                
                damage = max(1.0, total_attack - target.armor)
                
                target.hp -= damage
                self.reload_timer = self.reload_time
                
                if target.hp <= 0:
                    target.alive = False
                    target.hp = 0
                    engine.mark_dead(target)
        else:
            self.move_towards(target, dt)

    def move_towards(self, target: "Unit", dt: float):
        dx = target.x - self.x
        dy = target.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 1e-6:
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt