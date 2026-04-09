import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from network_integration import (
    OwnershipState,
    attach_to_existing_engine,
    example_tick_usage,
    integrate_network,
)
from p2p_client import P2PClient


@dataclass
class Entity:
    entity_id: str
    x: int = 0
    y: int = 0
    hp: int = 100


@dataclass
class GameState:
    entities: Dict[str, Entity] = field(default_factory=dict)

    def ensure_entity(self, entity_id: str) -> Entity:
        if entity_id not in self.entities:
            self.entities[entity_id] = Entity(entity_id=entity_id)
        return self.entities[entity_id]


def move_unit(player: str, x: int, y: int) -> None:
    """Example adapter for your real engine move_unit(player, x, y)."""
    ent = GAME_STATE.ensure_entity(player)
    ent.x = x
    ent.y = y
    print(f"[APPLY] MOVE {player} -> ({x}, {y})")


def attack_unit(attacker: str, target: str) -> None:
    """Example adapter for your real engine attack_unit(attacker, target)."""
    _ = attacker
    target_ent = GAME_STATE.ensure_entity(target)
    target_ent.hp = max(0, target_ent.hp - 10)
    print(f"[APPLY] ATTACK {attacker} -> {target} (hp={target_ent.hp})")


def ai_decide_move(player_name: str, tick: int) -> Tuple[int, int]:
    x = 10 + tick
    y = 5 + tick
    return x, y


def collect_local_ai_actions(player_name: str, tick: int) -> List[dict]:
    """
    Convert local AI decisions into the canonical outbound action format.
    This list is sent each tick via send_ai_action().
    """
    x, y = ai_decide_move(player_name, tick)
    actions: List[dict] = [
        {
            "type": "MOVE",
            "player": player_name,
            "x": x,
            "y": y,
            "entity_id": player_name,
        }
    ]

    if tick % 5 == 0:
        actions.append(
            {
                "type": "ATTACK",
                "player": player_name,
                "target": "enemy2",
                "entity_id": player_name,
            }
        )

    return actions


GAME_STATE = GameState()


def game_loop_example() -> None:
    """
    Modular integration example for a real game loop:
    1) local AI builds outbound actions each tick
    2) actions are sent to local C node through P2PClient
    3) inbound messages are drained from a thread-safe queue and applied
    4) move_unit()/attack_unit() represent existing engine hooks
    """
    player_name = "playerA"
    net = P2PClient(host="127.0.0.1", port=9001)
    net.connect()
    net.start_receiver_thread()
    net.send_message(f"HELLO|python|{player_name}")

    # Optional week-2 extension: enforce ownership before edits.
    ownership = OwnershipState(local_player=player_name)

    integrator = attach_to_existing_engine(
        game_state=GAME_STATE,
        client=net,
        move_unit_fn=move_unit,
        attack_unit_fn=attack_unit,
        ownership=ownership,
    )

    try:
        for tick in range(1, 21):
            # 1) OUTBOUND: local AI -> action dicts -> protocol messages.
            local_actions = collect_local_ai_actions(player_name, tick)
            example_tick_usage(integrator, local_actions)

            # 2) INBOUND: process queued messages without blocking the tick.
            integrate_network(GAME_STATE, net, integrator)

            # 3) Render/update hooks can run here.
            # renderer.sync_from_game_state(GAME_STATE)

            time.sleep(0.1)
    finally:
        net.close()


if __name__ == "__main__":
    game_loop_example()
