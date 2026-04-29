from __future__ import annotations

from dataclasses import dataclass, field
from queue import Empty
from typing import Any, Callable, Dict, Iterable, Optional

from p2p_client import P2PClient


Action = Dict[str, Any]
MoveUnitFn = Callable[[str, int, int], None]
AttackUnitFn = Callable[[str, str], None]


@dataclass
class OwnershipState:
    """
    Optional ownership helper.

    - entity_owner tracks who currently owns each entity.
    - owned_entities tracks entities owned by this local player.
    """

    local_player: str
    entity_owner: Dict[str, str] = field(default_factory=dict)
    owned_entities: set[str] = field(default_factory=set)

    def can_modify(self, entity_id: str) -> bool:
        owner = self.entity_owner.get(entity_id)
        return owner is None or owner == self.local_player

    def request_ownership(self, entity_id: str, client: P2PClient) -> None:
        client.send_message(f"REQUEST_OWNERSHIP|{entity_id}")

    def grant_ownership(self, entity_id: str, owner_player: str, client: Optional[P2PClient] = None) -> None:
        self.entity_owner[entity_id] = owner_player
        if owner_player == self.local_player:
            self.owned_entities.add(entity_id)
        else:
            self.owned_entities.discard(entity_id)

        if client is not None:
            client.send_message(f"GRANT_OWNERSHIP|{entity_id}")


@dataclass
class NetworkIntegrator:
    """
    Integrates P2P client messaging with your game loop.

    Usage each tick:
      1) integrator.send_ai_action(action) for each local AI action
      2) integrator.integrate_network() to apply all inbound messages
    """

    game_state: Any
    client: P2PClient
    move_unit_fn: MoveUnitFn
    attack_unit_fn: AttackUnitFn
    ownership: Optional[OwnershipState] = None

    def send_ai_action(self, action: Action) -> None:
        """Outbound: convert local AI action dict to protocol message and send."""
        msg = _action_to_protocol(action)
        if msg is None:
            return

        if self.ownership is not None:
            entity_id = str(action.get("entity_id", ""))
            if entity_id and not self.ownership.can_modify(entity_id):
                self.ownership.request_ownership(entity_id, self.client)
                return

        self.client.send_message(msg)

    def process_incoming_message(self, msg: str) -> None:
        """Inbound: parse one message and apply to local game state using engine callbacks."""
        process_incoming_message(
            msg=msg,
            game_state=self.game_state,
            move_unit_fn=self.move_unit_fn,
            attack_unit_fn=self.attack_unit_fn,
            ownership=self.ownership,
        )

    def integrate_network(self) -> None:
        """Drain queued inbound messages without blocking the game loop."""
        while True:
            try:
                msg = self.client.incoming_queue.get_nowait()
            except Empty:
                break
            self.process_incoming_message(msg)


def _action_to_protocol(action: Action) -> Optional[str]:
    action_type = str(action.get("type", "")).upper()

    if action_type == "MOVE":
        player = str(action["player"])
        x = int(action["x"])
        y = int(action["y"])
        return f"MOVE|{player}|{x}|{y}"

    if action_type == "ATTACK":
        player = str(action["player"])
        target = str(action["target"])
        return f"ATTACK|{player}|{target}"

    if action_type == "REQUEST_OWNERSHIP":
        entity_id = str(action["entity_id"])
        return f"REQUEST_OWNERSHIP|{entity_id}"

    if action_type == "GRANT_OWNERSHIP":
        entity_id = str(action["entity_id"])
        return f"GRANT_OWNERSHIP|{entity_id}"

    return None


def process_incoming_message(
    msg: str,
    game_state: Any,
    move_unit_fn: MoveUnitFn,
    attack_unit_fn: AttackUnitFn,
    ownership: Optional[OwnershipState] = None,
) -> None:
    """
    Standalone parser+applier for one protocol message.

    MOVE|player|x|y
    ATTACK|player|target
    REQUEST_OWNERSHIP|entity_id
    GRANT_OWNERSHIP|entity_id
    """
    parts = msg.strip().split("|")
    if not parts or not parts[0]:
        return

    msg_type = parts[0].upper()

    if msg_type == "MOVE" and len(parts) == 4:
        player = parts[1]
        x = int(float(parts[2]))
        y = int(float(parts[3]))
        move_unit_fn(player, x, y)
        return

    if msg_type == "ATTACK" and len(parts) == 3:
        player = parts[1]
        target = parts[2]
        attack_unit_fn(player, target)
        return

    if ownership is None:
        return

    if msg_type == "REQUEST_OWNERSHIP" and len(parts) == 2:
        entity_id = parts[1]
        # Week 2 policy hook: for now, first writer keeps ownership by default.
        if entity_id not in ownership.entity_owner:
            ownership.grant_ownership(entity_id, ownership.local_player)
        return

    if msg_type == "GRANT_OWNERSHIP" and len(parts) == 2:
        entity_id = parts[1]
        ownership.grant_ownership(entity_id, ownership.local_player)


def integrate_network(game_state: Any, client: P2PClient, integrator: NetworkIntegrator) -> None:
    """
    Helper function requested in the prompt.

    Call once per tick after local AI decisions are produced and before render.
    """
    _ = game_state
    _ = client
    integrator.integrate_network()


def attach_to_existing_engine(
    game_state: Any,
    client: P2PClient,
    move_unit_fn: MoveUnitFn,
    attack_unit_fn: AttackUnitFn,
    ownership: Optional[OwnershipState] = None,
) -> NetworkIntegrator:
    """
    Factory helper to create a configured integrator.

    Example:
      net = attach_to_existing_engine(engine, client, move_unit, attack_unit)
    """
    return NetworkIntegrator(
        game_state=game_state,
        client=client,
        move_unit_fn=move_unit_fn,
        attack_unit_fn=attack_unit_fn,
        ownership=ownership,
    )


def example_tick_usage(
    integrator: NetworkIntegrator,
    ai_actions: Iterable[Action],
) -> None:
    """
    Tick template:
      - outbound AI actions
      - inbound network messages
    """
    for action in ai_actions:
        integrator.send_ai_action(action)

    integrator.integrate_network()
