from dataclasses import dataclass, field
from Map import MAP_W, MAP_H
from Units import Unit
from Generals import General
from typing import List, Dict
@dataclass
class SimpleEngine:
    w: int = MAP_W
    h: int = MAP_H
    units: List[Unit] = field(default_factory=list)
    units_by_id: Dict[int, Unit] = field(default_factory=dict)
    next_unit_id: int = 1
    tick: float = 0.0
    events: List[str] = field(default_factory=list)

    def spawn_unit(self, player: int, x: float, y: float, **kwargs) -> Unit:
        u = Unit(id=self.next_unit_id, player=player, x=x, y=y, **kwargs)
        # Ensure hp default if not passed
        if u.hp == 0.0:
            u.hp = kwargs.get('hp', 55)
        self.next_unit_id += 1
        self.units.append(u)
        self.units_by_id[u.id] = u
        return u

    def step(self, dt: float, generals: Dict[int, "General"]):
        self.tick += dt
        for pid, gen in generals.items():
            gen.give_orders(self)
        for u in list(self.units):
            if u.alive:
                u.step(dt, self)
        self.units = [u for u in self.units if u.alive]
        self.units_by_id = {u.id: u for u in self.units}
    def mark_dead(self, unit: Unit):
        self.events.append(f"Unit {unit.id} (P{unit.player}) died at tick {self.tick:.2f}")

    def get_units_for_player(self, player: int) -> List[Unit]:
        return [u for u in self.units if u.player == player and u.alive]