from __future__ import annotations

from dataclasses import dataclass, field
from queue import Empty
from typing import Any, Callable, Dict, Optional, Tuple, List
from enum import Enum
import hashlib

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
class CoherenceValidator:
    """Verify game state coherence between players using checksums."""
    
    local_player: int
    
    def compute_state_hash(self, engine: Any) -> str:
        """
        Compute deterministic hash of current game state.
        Used to verify both players have coherent view.
        """
        state_items = []
        
        # Hash all alive units with their core state
        for unit in sorted(engine.units, key=lambda u: u.id):
            if unit.alive:
                item = f"{unit.id}:{unit.player}:{unit.x:.2f}:{unit.y:.2f}:{unit.hp:.1f}:{unit.target_id}"
                state_items.append(item)
        
        state_str = "|".join(state_items)
        return hashlib.md5(state_str.encode()).hexdigest()
    
    def validate_remote_hash(self, local_hash: str, remote_hash: str) -> Tuple[bool, Optional[str]]:
        """
        Compare local and remote state hashes.
        Returns (coherent, reason_if_not)
        """
        if local_hash == remote_hash:
            return True, None
        return False, f"State mismatch: local={local_hash[:8]}... vs remote={remote_hash[:8]}..."
    
    def get_state_snapshot(self, engine: Any) -> str:
        """Serialize full game state for transmission."""
        state_lines = []
        for unit in sorted(engine.units, key=lambda u: u.id):
            if unit.alive:
                state_lines.append(
                    f"UNIT|{unit.id}|{unit.player}|{unit.x:.3f}|{unit.y:.3f}|{unit.hp:.1f}|{unit.target_id if unit.target_id else -1}"
                )
        return "|".join(state_lines)


@dataclass
class PlayerJoinHandler:
    """Handle new player arrival and initial state synchronization."""
    
    local_player: int
    
    def generate_join_announcement(self) -> str:
        """Generate PLAYER_JOINED message."""
        return f"PLAYER_JOINED|{self.local_player}"
    
    def request_full_state(self, client: P2PClient) -> None:
        """Request full game state from existing players."""
        client.send_message(f"REQUEST_FULL_STATE|{self.local_player}")
    
    def handle_unit_placement_conflict(
        self,
        new_unit_x: float,
        new_unit_y: float,
        existing_units: List[Any],
        collision_radius: float = 2.0
    ) -> Tuple[float, float]:
        """
        Resolve unit placement conflicts when new player arrives.
        Moves unit away from occupied positions.
        Returns (new_x, new_y)
        """
        import math
        
        test_x, test_y = new_unit_x, new_unit_y
        
        # Check for collisions
        for existing_unit in existing_units:
            dist = math.hypot(test_x - existing_unit.x, test_y - existing_unit.y)
            if dist < collision_radius:
                # Move away from collision
                angle = math.atan2(test_y - existing_unit.y, test_x - existing_unit.x)
                test_x = existing_unit.x + collision_radius * math.cos(angle)
                test_y = existing_unit.y + collision_radius * math.sin(angle)
        
        return test_x, test_y


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
    
    NEW: On player join:
    1) Announce arrival
    2) Request full state
    3) Receive state snapshot
    4) Place initial units with conflict resolution
    5) Verify coherence with state hashes
    """
    
    engine: Any  # SimpleEngine
    client: P2PClient
    ownership: OwnershipTracker
    local_player: int
    coherence: Optional[CoherenceValidator] = None
    join_handler: Optional[PlayerJoinHandler] = None
    remote_player_count: int = 0
    has_announced_join: bool = False
    
    def __post_init__(self):
        if self.coherence is None:
            self.coherence = CoherenceValidator(local_player=self.local_player)
        if self.join_handler is None:
            self.join_handler = PlayerJoinHandler(local_player=self.local_player)
    
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
        
        # New player arrival
        if msg_type == "PLAYER_JOINED":
            self._handle_player_joined(parts)
            return
        
        # Full state request
        if msg_type == "REQUEST_FULL_STATE":
            self._handle_request_full_state(parts)
            return
        
        # Full state sync
        if msg_type == "FULL_STATE_SYNC" and len(parts) >= 2:
            self._handle_full_state_sync(parts)
            return
        
        # Individual unit from state sync
        if msg_type == "UNIT" and len(parts) >= 8:
            self._handle_synced_unit(parts)
            return
        
        # State hash for coherence verification
        if msg_type == "STATE_HASH" and len(parts) == 2:
            self._handle_state_hash(parts)
            return
        
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
    
    def _handle_player_joined(self, parts: list) -> None:
        """Handle notification of new player arrival."""
        try:
            player_id = int(parts[1])
        except (ValueError, IndexError):
            return
        
        if player_id == self.local_player:
            return  # Ignore our own join announcement
        
        self.remote_player_count += 1
        self.engine.events.append(f"Player {player_id} joined the game")
    
    def _handle_request_full_state(self, parts: list) -> None:
        """Remote player requesting full state snapshot."""
        try:
            requesting_player = int(parts[1])
        except (ValueError, IndexError):
            return
        
        if requesting_player == self.local_player:
            return
        
        # Send full state
        self.publish_full_state()
    
    def _handle_full_state_sync(self, parts: list) -> None:
        """Receive full state sync during new player arrival."""
        # Full state is sent as multiple UNIT messages, followed by this marker
        self.engine.events.append("Full state sync received from remote player")
    
    def _handle_synced_unit(self, parts: list) -> None:
        """Process unit from full state sync: UNIT|unit_id|player|x|y|hp|target_id"""
        try:
            unit_id = int(parts[1])
            player = int(parts[2])
            x = float(parts[3])
            y = float(parts[4])
            hp = float(parts[5])
            target_id = int(parts[6]) if int(parts[6]) != -1 else None
        except (ValueError, IndexError):
            return
        
        # Check if unit already exists
        if unit_id in self.engine.units_by_id:
            unit = self.engine.units_by_id[unit_id]
            # Resolve conflict: keep existing, but log it
            self.engine.events.append(
                f"Unit {unit_id} conflict on join: existing vs remote. Kept existing."
            )
            return
        
        # Spawn unit from remote state
        try:
            # Resolve placement conflicts
            resolved_x, resolved_y = self.join_handler.handle_unit_placement_conflict(
                x, y,
                self.engine.units,
                collision_radius=2.0
            )
            
            # Manually create unit in engine with resolved position
            new_unit = self.engine.spawn_unit(
                player, 
                resolved_x, 
                resolved_y,
                hp=hp,
                target_id=target_id
            )
            
            # Assign ownership to remote player
            self.ownership.grant_ownership(unit_id, player)
            
            if (resolved_x, resolved_y) != (x, y):
                self.engine.events.append(
                    f"Unit {unit_id} placement adjusted from ({x:.1f},{y:.1f}) to ({resolved_x:.1f},{resolved_y:.1f}) "
                    f"due to conflict resolution"
                )
        except Exception as e:
            self.engine.events.append(f"Error syncing unit {unit_id}: {str(e)}")
    
    def _handle_state_hash(self, parts: list) -> None:
        """Receive state hash for coherence verification."""
        try:
            remote_hash = parts[1]
        except IndexError:
            return
        
        local_hash = self.coherence.compute_state_hash(self.engine)
        coherent, reason = self.coherence.validate_remote_hash(local_hash, remote_hash)
        
        if coherent:
            self.engine.events.append("✓ State coherence verified")
        else:
            self.engine.events.append(f"✗ STATE DIVERGENCE: {reason}")
    
    def announce_join(self) -> None:
        """Announce this player's arrival to remote players."""
        if not self.has_announced_join:
            msg = self.join_handler.generate_join_announcement()
            self.client.send_message(msg)
            self.has_announced_join = True
    
    def request_full_state_from_remote(self) -> None:
        """Request current game state from remote players."""
        self.join_handler.request_full_state(self.client)
    
    def publish_full_state(self) -> None:
        """Send complete game state to remote players."""
        # Send all units as UNIT messages
        for unit in self.engine.units:
            if unit.alive:
                msg = f"UNIT|{unit.id}|{unit.player}|{unit.x:.3f}|{unit.y:.3f}|{unit.hp:.1f}|{unit.target_id if unit.target_id else -1}"
                self.client.send_message(msg)
        
        # Send completion marker
        self.client.send_message("FULL_STATE_SYNC|end")
    
    def publish_state_hash(self) -> None:
        """Publish state hash for coherence verification."""
        state_hash = self.coherence.compute_state_hash(self.engine)
        self.client.send_message(f"STATE_HASH|{state_hash}")
    
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
