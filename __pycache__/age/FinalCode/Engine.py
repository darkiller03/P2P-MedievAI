from dataclasses import dataclass, field
from Map import MAP_W, MAP_H
from Units import Unit
from Generals import General
from typing import List, Dict, Optional
@dataclass
class SimpleEngine:
    w: int = MAP_W
    h: int = MAP_H
    units: List[Unit] = field(default_factory=list)
    units_by_id: Dict[int, Unit] = field(default_factory=dict)
    next_unit_id: int = 1
    tick: float = 0.0
    events: List[str] = field(default_factory=list)
    # Ownership system: maps unit_id -> owner_player_id
    unit_ownership: Dict[int, int] = field(default_factory=dict)
    # Pending ownership requests: unit_id -> requesting_player_id
    pending_ownership: Dict[int, int] = field(default_factory=dict)

    def spawn_unit(self, player: int, x: float, y: float, **kwargs) -> Unit:
        u = Unit(id=self.next_unit_id, player=player, x=x, y=y, **kwargs)
        # Ensure hp default if not passed
        if u.hp == 0.0:
            u.hp = kwargs.get('hp', 55)
        self.next_unit_id += 1
        self.units.append(u)
        self.units_by_id[u.id] = u
        # Auto-assign ownership to spawning player
        self.unit_ownership[u.id] = player
        return u

    def can_modify_unit(self, unit_id: int, player: int) -> bool:
        """Check if a player can modify a unit (ownership enforcement)."""
        owner = self.unit_ownership.get(unit_id)
        # If no owner, first player to request owns it
        if owner is None:
            return True
        return owner == player

    def request_ownership(self, unit_id: int, requesting_player: int) -> bool:
        """Request ownership of a unit. Returns True if request can be granted immediately."""
        if unit_id not in self.units_by_id:
            return False
        owner = self.unit_ownership.get(unit_id)
        if owner is None or owner == requesting_player:
            # Grant ownership
            self.unit_ownership[unit_id] = requesting_player
            self.events.append(f"Unit {unit_id} ownership granted to player {requesting_player} at tick {self.tick:.2f}")
            return True
        # Owner exists and it's not this player - request pending
        self.pending_ownership[unit_id] = requesting_player
        return False

    def grant_ownership(self, unit_id: int, new_owner: int) -> None:
        """Grant ownership of a unit to a player."""
        if unit_id in self.units_by_id:
            self.unit_ownership[unit_id] = new_owner
            self.pending_ownership.pop(unit_id, None)
            self.events.append(f"Unit {unit_id} ownership transferred to player {new_owner} at tick {self.tick:.2f}")

    def step(self, dt: float, generals: Dict[int, "General"]):
        self.tick += dt
        for pid, gen in generals.items():
            gen.give_orders(self)
        for u in list(self.units):
            if u.alive:
                u.step(dt, self)
        self.units = [u for u in self.units if u.alive]
        self.units_by_id = {u.id: u for u in self.units}
        # Clean up ownership for dead units
        dead_ids = set(self.unit_ownership.keys()) - set(u.id for u in self.units)
        for unit_id in dead_ids:
            self.unit_ownership.pop(unit_id, None)
            self.pending_ownership.pop(unit_id, None)

    def mark_dead(self, unit: Unit):
        self.events.append(f"Unit {unit.id} (P{unit.player}) died at tick {self.tick:.2f}")
        self.unit_ownership.pop(unit.id, None)
        self.pending_ownership.pop(unit.id, None)

    def get_units_for_player(self, player: int) -> List[Unit]:
        return [u for u in self.units if u.player == player and u.alive]