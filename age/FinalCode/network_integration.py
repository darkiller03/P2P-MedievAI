from __future__ import annotations

from dataclasses import dataclass, field
from queue import Empty
from typing import Any, Callable, Dict, Optional, Tuple
from enum import Enum

from p2p_client import P2PClient


class OwnershipState(Enum):
    """Ownership states during the workflow."""
    UNOWNED = "unowned"
    REQUESTING = "requesting"
    OWNED = "owned"


@dataclass
class OwnershipTracker:
    """
    Complete ownership workflow implementation.
    
    Phases:
    1) Request: LOCAL player wants to modify unit owned by REMOTE player
    2) Verify: REMOTE player receives request, checks feasibility
    3) Grant: REMOTE sends ownership grant with current state
    4) Execute: LOCAL player performs action with verified ownership + state
    5) Publish: LOCAL publishes result to all
    """
    
    local_player: int
    entity_owner: Dict[int, int] = field(default_factory=dict)  # unit_id -> player_id
    ownership_state: Dict[int, OwnershipState] = field(default_factory=dict)  # unit_id -> state
    granted_state: Dict[int, Dict[str, Any]] = field(default_factory=dict)  # unit_id -> state snapshot
    
    def can_modify_local(self, unit_id: int) -> bool:
        """Check if local player owns the unit."""
        owner = self.entity_owner.get(unit_id)
        return owner == self.local_player
    
    def is_unowned(self, unit_id: int) -> bool:
        """Check if unit is unowned."""
        return unit_id not in self.entity_owner
    
    def request_ownership(self, unit_id: int, client: P2PClient) -> None:
        """Phase 1: Request ownership from remote owner."""
        self.ownership_state[unit_id] = OwnershipState.REQUESTING
        client.send_message(f"REQUEST_OWNERSHIP|{unit_id}")
    
    def grant_ownership(self, unit_id: int, new_owner: int, unit_state: Optional[Dict[str, Any]] = None) -> None:
        """Phase 3: Grant ownership with current state snapshot."""
        self.entity_owner[unit_id] = new_owner
        self.ownership_state[unit_id] = OwnershipState.OWNED
        if unit_state:
            self.granted_state[unit_id] = unit_state
    
    def revoke_ownership(self, unit_id: int) -> None:
        """Revoke ownership when done."""
        if unit_id in self.entity_owner:
            self.entity_owner.pop(unit_id, None)
            self.ownership_state.pop(unit_id, None)
            self.granted_state.pop(unit_id, None)


@dataclass
class NetworkIntegrator:
    """
    Complete network integration with ownership enforcement.
    
    Action flow:
    1) Local AI wants to move/attack unit
    2) Check ownership - if remote, request it
    3) On grant, verify action is valid
    4) Execute action locally
    5) Broadcast result to all players
    """
    
    engine: Any  # SimpleEngine
    client: P2PClient
    ownership: OwnershipTracker
    local_player: int
    
    def can_execute_action(self, action: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Verify if action is valid before execution.
        Returns (can_execute, reason_if_not)
        """
        action_type = action.get("type", "").upper()
        unit_id = action.get("unit_id")
        
        if not unit_id:
            return True, None  # No unit specified, proceed
        
        unit = self.engine.units_by_id.get(unit_id)
        if not unit:
            return False, f"Unit {unit_id} not found"
        
        if not unit.alive:
            return False, f"Unit {unit_id} is dead"
        
        # Check ownership
        if not self.ownership.can_modify_local(unit_id):
            if self.ownership.is_unowned(unit_id):
                # Will be handled by request_ownership
                return False, f"Unit {unit_id} unowned - ownership requested"
            return False, f"Unit {unit_id} owned by player {self.ownership.entity_owner.get(unit_id)}"
        
        # Type-specific verification
        if action_type == "MOVE":
            target_x = action.get("x")
            target_y = action.get("y")
            if target_x is None or target_y is None:
                return False, "MOVE requires x, y coordinates"
            if not (0 <= target_x < self.engine.w and 0 <= target_y < self.engine.h):
                return False, f"Target ({target_x}, {target_y}) outside map bounds"
            return True, None
        
        if action_type == "ATTACK":
            target_id = action.get("target_id")
            target = self.engine.units_by_id.get(target_id)
            if not target:
                return False, f"Target unit {target_id} not found"
            if not target.alive:
                return False, f"Target unit {target_id} is dead"
            if target.player == unit.player:
                return False, f"Cannot attack own unit"
            
            dist = unit.distance_to(target)
            if dist > unit.range + 5:
                return False, f"Target too far (dist={dist:.1f}, range={unit.range})"
            
            return True, None
        
        return True, None
    
    def send_action_with_ownership(self, action: Dict[str, Any]) -> bool:
        """
        Send action, requesting ownership if needed.
        Returns True if action was sent, False if waiting for ownership.
        """
        unit_id = action.get("unit_id")
        
        if not unit_id:
            # No unit specified, send immediately
            msg = self._action_to_protocol(action)
            if msg:
                self.client.send_message(msg)
            return True
        
        # Check ownership
        if self.ownership.is_unowned(unit_id):
            # Request ownership
            self.ownership.request_ownership(unit_id, self.client)
            return False
        
        if not self.ownership.can_modify_local(unit_id):
            # Already requested or owned by someone else
            state = self.ownership.ownership_state.get(unit_id)
            if state == OwnershipState.REQUESTING:
                return False  # Still waiting
            return False  # Owned by someone else
        
        # We own it - verify and send
        can_exec, reason = self.can_execute_action(action)
        if not can_exec:
            self.engine.events.append(f"Action rejected: {reason}")
            return False
        
        msg = self._action_to_protocol(action)
        if msg:
            self.client.send_message(msg)
        return True
    
    def process_incoming_message(self, msg: str) -> None:
        """Process one incoming network message."""
        parts = msg.strip().split("|")
        if not parts or not parts[0]:
            return
        
        msg_type = parts[0].upper()
        
        # Update state
        if msg_type == "STATE" and len(parts) >= 8:
            self._handle_state(parts)
            return
        
        # Movement
        if msg_type == "MOVE" and len(parts) >= 4:
            self._handle_move(parts)
            return
        
        # Attack
        if msg_type == "ATTACK" and len(parts) >= 4:
            self._handle_attack(parts)
            return
        
        # Ownership requests from remote player
        if msg_type == "REQUEST_OWNERSHIP" and len(parts) == 2:
            self._handle_request_ownership(parts)
            return
        
        # Ownership grant from remote owner
        if msg_type == "GRANT_OWNERSHIP" and len(parts) >= 2:
            self._handle_grant_ownership(parts)
            return
    
    def _handle_request_ownership(self, parts: list) -> None:
        """Phase 2: Remote player requests ownership."""
        try:
            unit_id = int(parts[1])
        except (ValueError, IndexError):
            return
        
        unit = self.engine.units_by_id.get(unit_id)
        if not unit:
            return
        
        # Check if we own it
        owner = self.ownership.entity_owner.get(unit_id)
        if owner != self.local_player:
            # We don't own it, ignore
            return
        
        # Verify action is allowed (implicit grant if uncontested)
        # Grant with current state snapshot
        state_snapshot = {
            "x": unit.x,
            "y": unit.y,
            "hp": unit.hp,
            "target_id": unit.target_id,
            "alive": unit.alive
        }
        
        msg = f"GRANT_OWNERSHIP|{unit_id}|{unit.x:.3f}|{unit.y:.3f}|{unit.hp:.3f}|{1 if unit.alive else 0}|{unit.target_id if unit.target_id else -1}"
        self.client.send_message(msg)
    
    def _handle_grant_ownership(self, parts: list) -> None:
        """Phase 3: Receive ownership grant with state."""
        try:
            unit_id = int(parts[1])
        except (ValueError, IndexError):
            return
        
        # Parse state if provided
        state = {}
        if len(parts) >= 7:
            try:
                state["x"] = float(parts[2])
                state["y"] = float(parts[3])
                state["hp"] = float(parts[4])
                state["alive"] = int(parts[5]) == 1
                state["target_id"] = int(parts[6]) if int(parts[6]) != -1 else None
            except (ValueError, IndexError):
                pass
        
        # Grant ownership to us
        self.ownership.grant_ownership(unit_id, self.local_player, state)
        self.engine.events.append(f"Ownership granted for unit {unit_id}")
    
    def _handle_state(self, parts: list) -> None:
        """Apply remote state update: STATE|unit_id|x|y|hp|alive|target_id"""
        try:
            unit_id = int(parts[1])
            x = float(parts[2])
            y = float(parts[3])
            hp = float(parts[4])
            alive = int(parts[5]) == 1
            target_id = int(parts[6]) if int(parts[6]) != -1 else None
        except (ValueError, IndexError):
            return
        
        unit = self.engine.units_by_id.get(unit_id)
        if not unit:
            return
        
        # Only apply if we don't own it (remote authority)
        if self.ownership.can_modify_local(unit_id):
            return
        
        unit.x = x
        unit.y = y
        unit.hp = hp
        unit.target_id = target_id
        
        if not alive and unit.alive:
            unit.alive = False
    
    def _handle_move(self, parts: list) -> None:
        """MOVE|unit_id|x|y - from remote player"""
        try:
            unit_id = int(parts[1])
            x = float(parts[2])
            y = float(parts[3])
        except (ValueError, IndexError):
            return
        
        unit = self.engine.units_by_id.get(unit_id)
        if not unit or not unit.alive:
            return
        
        # Only apply if we don't own it
        if self.ownership.can_modify_local(unit_id):
            return
        
        unit.x = x
        unit.y = y
    
    def _handle_attack(self, parts: list) -> None:
        """ATTACK|unit_id|target_id - from remote player"""
        try:
            unit_id = int(parts[1])
            target_id = int(parts[2])
        except (ValueError, IndexError):
            return
        
        unit = self.engine.units_by_id.get(unit_id)
        target = self.engine.units_by_id.get(target_id)
        
        if not unit or not unit.alive or not target or not target.alive:
            return
        
        # Only apply if we don't own attacker
        if self.ownership.can_modify_local(unit_id):
            return
        
        unit.target_id = target.id
    
    def _action_to_protocol(self, action: Dict[str, Any]) -> Optional[str]:
        """Convert action dict to protocol message."""
        action_type = action.get("type", "").upper()
        unit_id = action.get("unit_id")
        
        if action_type == "MOVE" and unit_id:
            x = action.get("x")
            y = action.get("y")
            if x is not None and y is not None:
                return f"MOVE|{unit_id}|{x:.3f}|{y:.3f}"
        
        if action_type == "ATTACK" and unit_id:
            target_id = action.get("target_id")
            if target_id:
                return f"ATTACK|{unit_id}|{target_id}"
        
        if action_type == "REQUEST_OWNERSHIP" and unit_id:
            return f"REQUEST_OWNERSHIP|{unit_id}"
        
        if action_type == "GRANT_OWNERSHIP" and unit_id:
            return f"GRANT_OWNERSHIP|{unit_id}"
        
        return None
    
    def integrate_network(self) -> None:
        """Drain and process all incoming messages this tick."""
        while True:
            try:
                msg = self.client.incoming_queue.get_nowait()
            except Empty:
                break
            self.process_incoming_message(msg)
    
    def publish_unit_state(self, unit_id: int) -> None:
        """Publish unit state to all remote players."""
        unit = self.engine.units_by_id.get(unit_id)
        if not unit:
            return
        
        msg = f"STATE|{unit_id}|{unit.x:.3f}|{unit.y:.3f}|{unit.hp:.3f}|{1 if unit.alive else 0}|{unit.target_id if unit.target_id else -1}"
        self.client.send_message(msg)
