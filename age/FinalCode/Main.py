import argparse
import sys
import os
# Add parent directories to path so we can import battle_plot from AgeOfEmpire/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from Map import MAP_W, MAP_H
from typing import List, Dict, Optional, Tuple
from Engine import SimpleEngine
from Scenario import square_scenario, chevron_scenario, optimal_scenario, echelon_scenario, tiny_scenario
import random
import curses
import time
from Generals import DaftGeneral, BrainDeadGeneral, New_General_1, New_General_2, New_General_3, GenghisKhanPrimeGeneral
from Scenario_lanchester import lanchester_scenario
from battle_plot import generate_lanchester_plot
from p2p_client import P2PClient
from NetworkMetrics import get_global_metrics, reset_metrics


class PassiveGeneral:
    """General used for remote-controlled players in network mode."""

    def __init__(self, player: int):
        self.player = player

    def give_orders(self, engine: SimpleEngine):
        _ = engine


class NetworkBridge:
    """
    Bridges engine state and local C P2P node.

    VERSION 1 (Best-effort, no guarantees):
    - inbound: drains async queue without blocking game loop
    - outbound: publishes local player's unit updates
    - PLAYER_JOINED: synchronizes initial state when a player joins
    - Inconsistency tracking: logs races, state mismatches, concurrent modifications
    """

    def __init__(self, host: str, port: int, local_player: int):
        self.client = P2PClient(host=host, port=port)
        self.local_player = local_player
        self._last_processed_tick: Optional[float] = None
        self._last_sent_positions: Dict[int, Tuple[float, float]] = {}
        self._last_sent_targets: Dict[int, Optional[int]] = {}
        
        # V1: Inconsistency tracking
        self._remote_unit_states: Dict[int, Dict] = {}  # unit_id -> {x, y, hp, tick_updated}
        self._inconsistencies_log: List[str] = []
        self._message_timestamps: Dict[str, float] = {}  # For latency measurement
        self._state_sync_requested = False
        self._initial_sync_complete = False
        self.enable_debug_logging = True

    def connect(self) -> None:
        self.client.connect()
        self.client.start_receiver_thread()
        # Send HELLO and immediately announce PLAYER_JOINED for state synchronization
        self.client.send_message(f"HELLO|python|player{self.local_player}")
        self.client.send_message(f"PLAYER_JOINED|player{self.local_player}")
        self._state_sync_requested = True
        if self.enable_debug_logging:
            print(f"[NET] Connected as player{self.local_player}, requesting initial state sync")

    def close(self) -> None:
        self.client.close()

    def integrate_network(self, engine: SimpleEngine) -> None:
        # Engine calls generals for multiple players at same tick. Process queue once/tick.
        if self._last_processed_tick == engine.tick:
            return

        while True:
            raw = self.client.try_get_message()
            if raw is None:
                break
            self.process_incoming_message(raw, engine)

        self._last_processed_tick = engine.tick

    def send_ai_action(self, msg: str) -> None:
        self.client.send_message(msg)
        # V1: Record metric for outbound message
        get_global_metrics().record_message_sent()

    def publish_local_actions(self, engine: SimpleEngine) -> None:
        for u in engine.get_units_for_player(self.local_player):
            # Authoritative per-unit state replication keeps both simulations aligned.
            self.send_ai_action(
                f"STATE|player{u.player}|{u.id}|{u.x:.3f}|{u.y:.3f}|{u.hp:.3f}|{1 if u.alive else 0}|{u.target_id if u.target_id is not None else -1}"
            )

            prev_pos = self._last_sent_positions.get(u.id)
            current_pos = (round(u.x, 2), round(u.y, 2))
            if prev_pos != current_pos:
                self.send_ai_action(
                    f"MOVE|player{u.player}|{u.id}|{current_pos[0]}|{current_pos[1]}"
                )
                self._last_sent_positions[u.id] = current_pos

            prev_target = self._last_sent_targets.get(u.id)
            if u.target_id is not None and prev_target != u.target_id:
                self.send_ai_action(f"ATTACK|player{u.player}|{u.id}|{u.target_id}")
                self._last_sent_targets[u.id] = u.target_id

    def process_incoming_message(self, msg: str, engine: SimpleEngine) -> None:
        parts = msg.strip().split('|')
        if not parts:
            return

        kind = parts[0].upper()
        
        # V1: Handle initial state sync
        if kind == 'PLAYER_JOINED':
            self._handle_player_joined(parts, engine)
            return
        
        if kind == 'INITIAL_STATE_SYNC':
            self._handle_initial_state_sync(parts, engine)
            return
        
        if kind == 'HELLO':
            return

        if kind == 'MOVE':
            self._handle_move(parts, engine)
            return

        if kind == 'ATTACK':
            self._handle_attack(parts, engine)
            return

        if kind == 'STATE':
            self._handle_state(parts, engine)
            return

        if kind in ('REQUEST_OWNERSHIP', 'GRANT_OWNERSHIP'):
            # Ownership can be layered later without blocking base integration.
            return

    def move_unit(self, engine: SimpleEngine, unit_id: int, x: float, y: float) -> None:
        unit = engine.units_by_id.get(unit_id)
        if unit is None or not unit.alive:
            return
        unit.x = x
        unit.y = y

    def attack_unit(self, engine: SimpleEngine, attacker_id: int, target_id: int) -> None:
        attacker = engine.units_by_id.get(attacker_id)
        if attacker is None or not attacker.alive:
            return

        target = engine.units_by_id.get(target_id)
        if target is None or not target.alive:
            return

        attacker.target_id = target.id

    def _handle_move(self, parts: List[str], engine: SimpleEngine) -> None:
        # Preferred format: MOVE|playerX|unit_id|x|y
        if len(parts) == 5:
            player_id = self._parse_player(parts[1])
            if player_id is None or player_id == self.local_player:
                return
            unit_id = self._parse_int(parts[2])
            x = self._parse_float(parts[3])
            y = self._parse_float(parts[4])
            if unit_id is None or x is None or y is None:
                return
            self.move_unit(engine, unit_id, x, y)
            return

        # Legacy format fallback: MOVE|playerX|x|y
        if len(parts) == 4:
            player_id = self._parse_player(parts[1])
            x = self._parse_float(parts[2])
            y = self._parse_float(parts[3])
            if player_id is None or x is None or y is None:
                return
            units = engine.get_units_for_player(player_id)
            if units:
                self.move_unit(engine, units[0].id, x, y)

    def _handle_attack(self, parts: List[str], engine: SimpleEngine) -> None:
        # Preferred format: ATTACK|playerX|attacker_id|target_id
        if len(parts) == 4:
            player_id = self._parse_player(parts[1])
            if player_id is None or player_id == self.local_player:
                return
            attacker_id = self._parse_int(parts[2])
            target_id = self._parse_int(parts[3])
            if attacker_id is None or target_id is None:
                return
            self.attack_unit(engine, attacker_id, target_id)
            return

        # Legacy format fallback: ATTACK|playerX|target_id
        if len(parts) == 3:
            player_id = self._parse_player(parts[1])
            target_id = self._parse_int(parts[2])
            if player_id is None or target_id is None:
                return
            units = engine.get_units_for_player(player_id)
            if units:
                self.attack_unit(engine, units[0].id, target_id)

    def _handle_state(self, parts: List[str], engine: SimpleEngine) -> None:
        # Format: STATE|playerX|unit_id|x|y|hp|alive|target_id
        if len(parts) != 8:
            return

        player_id = self._parse_player(parts[1])
        if player_id is None or player_id == self.local_player:
            return

        unit_id = self._parse_int(parts[2])
        x = self._parse_float(parts[3])
        y = self._parse_float(parts[4])
        hp = self._parse_float(parts[5])
        alive_flag = self._parse_int(parts[6])
        target_id = self._parse_int(parts[7])

        if unit_id is None or x is None or y is None or hp is None or alive_flag is None:
            return

        unit = engine.units_by_id.get(unit_id)
        if unit is None:
            return

        # V1: Track inconsistencies before applying
        self._check_inconsistency(unit, x, y, hp, alive_flag == 1)

        unit.x = x
        unit.y = y
        unit.hp = hp
        unit.alive = alive_flag == 1
        unit.target_id = None if target_id is None or target_id < 0 else target_id

        # Store remote state for inconsistency detection
        self._remote_unit_states[unit_id] = {
            'x': x, 'y': y, 'hp': hp, 'alive': alive_flag == 1,
            'tick_updated': engine.tick
        }

    @staticmethod
    def _parse_player(text: str) -> Optional[int]:
        lower = text.lower()
        if lower.startswith('player'):
            return NetworkBridge._parse_int(lower.replace('player', '', 1))
        return NetworkBridge._parse_int(text)

    @staticmethod
    def _parse_int(text: str) -> Optional[int]:
        try:
            return int(float(text))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_float(text: str) -> Optional[float]:
        try:
            return float(text)
        except (TypeError, ValueError):
            return None

    # V1: New methods for state synchronization and inconsistency tracking
    
    def _handle_player_joined(self, parts: List[str], engine: SimpleEngine) -> None:
        """Handle PLAYER_JOINED from another player - send local state snapshot."""
        player_id = self._parse_player(parts[1]) if len(parts) > 1 else None
        if player_id is None or player_id == self.local_player:
            return
        
        if self.enable_debug_logging:
            print(f"[NET] Player {player_id} joined, sending local state snapshot")
        
        # Snapshot local units for the newcomer
        for u in engine.get_units_for_player(self.local_player):
            if u.alive:
                self.send_ai_action(
                    f"INITIAL_STATE_SYNC|player{self.local_player}|{u.id}|{u.x:.3f}|{u.y:.3f}|{u.hp:.3f}|{u.attack}|{u.range}|{u.speed}|{u.unit_type}"
                )
    
    def _handle_initial_state_sync(self, parts: List[str], engine: SimpleEngine) -> None:
        """Handle INITIAL_STATE_SYNC - receive snapshot from another player."""
        if len(parts) < 9:
            return
        
        player_id = self._parse_player(parts[1])
        if player_id is None or player_id == self.local_player:
            return
        
        unit_id = self._parse_int(parts[2])
        x = self._parse_float(parts[3])
        y = self._parse_float(parts[4])
        hp = self._parse_float(parts[5])
        attack = self._parse_float(parts[6])
        range_val = self._parse_float(parts[7])
        speed = self._parse_float(parts[8])
        unit_type = parts[9] if len(parts) > 9 else "Unit"
        
        if None in [unit_id, x, y, hp, attack, range_val, speed]:
            return
        
        # Check if unit already exists
        unit = engine.units_by_id.get(unit_id)
        if unit is None:
            # Create new unit from snapshot
            from Units import Unit
            unit = Unit(
                id=unit_id,
                player=player_id,
                x=x,
                y=y,
                hp=hp,
                attack=attack,
                range=range_val,
                speed=speed,
                alive=True,
                unit_type=unit_type
            )
            engine.units.append(unit)
            engine.units_by_id[unit_id] = unit
            if self.enable_debug_logging:
                print(f"[NET] Created unit {unit_id} for player{player_id} from initial sync")
        
        # Record remote state
        self._remote_unit_states[unit_id] = {
            'x': x, 'y': y, 'hp': hp, 'alive': True,
            'tick_updated': engine.tick
        }
    
    def _check_inconsistency(self, unit, remote_x: float, remote_y: float, remote_hp: float, remote_alive: bool) -> None:
        """V1: Detect and log state mismatches (races, concurrent modifications)."""
        metrics = get_global_metrics()
        inconsistencies = []
        
        # Position mismatch (unit moved differently locally and remotely)
        pos_distance = ((unit.x - remote_x) ** 2 + (unit.y - remote_y) ** 2) ** 0.5
        if pos_distance > 1.0:  # Threshold: 1 unit away
            inconsistencies.append(f"POSITION_RACE: unit_{unit.id} local={unit.x:.1f},{unit.y:.1f} vs remote={remote_x:.1f},{remote_y:.1f} dist={pos_distance:.2f}")
            metrics.record_race_condition(unit.id, "POSITION_RACE", (unit.x, unit.y), (remote_x, remote_y))
            metrics.record_state_mismatch(unit.id)
        
        # HP mismatch (different damage/healing)
        if abs(unit.hp - remote_hp) > 0.5:
            inconsistencies.append(f"HP_RACE: unit_{unit.id} local_hp={unit.hp:.1f} vs remote_hp={remote_hp:.1f}")
            metrics.record_race_condition(unit.id, "HP_RACE", unit.hp, remote_hp)
            metrics.record_state_mismatch(unit.id)
        
        # Alive mismatch
        if unit.alive != remote_alive:
            inconsistencies.append(f"ALIVE_RACE: unit_{unit.id} local_alive={unit.alive} vs remote_alive={remote_alive}")
            metrics.record_race_condition(unit.id, "ALIVE_RACE", unit.alive, remote_alive)
            metrics.record_state_mismatch(unit.id)
        
        for inc in inconsistencies:
            self._inconsistencies_log.append(inc)
            if self.enable_debug_logging:
                print(f"[NET INCONSISTENCY] {inc}")
    
    def get_inconsistency_report(self) -> Dict:
        """Return summary of detected inconsistencies (for V1 demonstration)."""
        return {
            'total_inconsistencies': len(self._inconsistencies_log),
            'position_races': len([i for i in self._inconsistencies_log if 'POSITION_RACE' in i]),
            'hp_races': len([i for i in self._inconsistencies_log if 'HP_RACE' in i]),
            'alive_races': len([i for i in self._inconsistencies_log if 'ALIVE_RACE' in i]),
            'log': self._inconsistencies_log[-20:]  # Last 20 for brief summary
        }


class NetworkedGeneral:
    """Wraps a local AI general and synchronizes with the network each tick."""

    def __init__(self, wrapped_general, bridge: NetworkBridge):
        self.wrapped_general = wrapped_general
        self.bridge = bridge

    def give_orders(self, engine: SimpleEngine):
        self.wrapped_general.give_orders(engine)


def configure_network_generals(
    generals: Dict[int, object],
    bridge: NetworkBridge,
    local_player: int,
) -> Dict[int, object]:
    configured: Dict[int, object] = {}
    for pid, general in generals.items():
        if pid == local_player:
            configured[pid] = NetworkedGeneral(general, bridge)
        else:
            configured[pid] = PassiveGeneral(pid)
    return configured


def get_ai_class(ai_name: str):
    """Get AI class by name"""
    ai_map = {
        'DaftGeneral': DaftGeneral,
        'BrainDeadGeneral': BrainDeadGeneral,
        'New_General_1': New_General_1,
        'New_General_2': New_General_2,
        'New_General_3': New_General_3,
        'DAFT': DaftGeneral,  # Short alias
        'BRAINDEAD': BrainDeadGeneral,  # Short alias
        'BrainDead': BrainDeadGeneral,  # Mixed case alias
        'Genghis' : GenghisKhanPrimeGeneral,
    }
    ai_class = ai_map.get(ai_name)
    if ai_class is None:
        print(f"Warning: AI '{ai_name}' not found. Available AIs: {', '.join(ai_map.keys())}")
        print(f"Using DaftGeneral as default.")
        return DaftGeneral
    return ai_class


def get_scenario(scenario_name: str):
    """Get scenario function by name"""
    scenario_map = {
        'square_scenario': square_scenario,
        'chevron_scenario': chevron_scenario,
        'optimal_scenario': optimal_scenario,
        'echelon_scenario': echelon_scenario,
        'lanchester_scenario': lanchester_scenario,
        'tiny_scenario': tiny_scenario
    }
    return scenario_map.get(scenario_name, square_scenario)


def run_battle(engine: SimpleEngine, generals: Dict, terminal_view: bool = False, datafile: str = None, net_bridge = None):
    """Run a single battle and optionally save results to file"""
    t = 0.0
    dt = 0.2
    step = 0
    start = time.time()
    max_ticks = 180.0
    
    # Run the simulation
    while t < max_ticks:
        # BEFORE step: process incoming network messages
        if net_bridge:
            net_bridge.integrate_network(engine)
            # Suppress verbose logging for cleaner output
            # print(f"[NET] Processed incoming messages at step {step}")
        
        engine.step(dt, generals)
        t += dt
        step += 1
        
        # AFTER step: send local unit actions to network
        if net_bridge:
            net_bridge.publish_local_actions(engine)
            # Suppress verbose logging for cleaner output
            # print(f"[NET] Published local actions at step {step}")
        
        p1 = engine.get_units_for_player(1)
        p2 = engine.get_units_for_player(2)
        if not p1 or not p2:
            winner = 2 if p2 else (1 if p1 else 0)
            break
    else:
        winner = 0  # Draw
    
    simulation_time = time.time() - start
    
    # Finalize metrics
    if net_bridge:
        get_global_metrics().finalize()
    
    # Print results
    print(f"Battle ended at t={t:.1f}s steps={step}. Winner: P{winner}")
    print(f"Simulation took {simulation_time:.2f}s wall time. Engine ticks: {engine.tick:.2f}")
    print("Events:")
    for e in engine.events[-20:]:
        print("  ", e)
    
    # V1: Print network inconsistencies and metrics
    if net_bridge:
        inconsistency_report = net_bridge.get_inconsistency_report()
        print(f"\n[V1 NETWORK ANALYSIS]")
        print(f"  Total inconsistencies detected: {inconsistency_report['total_inconsistencies']}")
        print(f"  Position races: {inconsistency_report['position_races']}")
        print(f"  HP races: {inconsistency_report['hp_races']}")
        print(f"  Alive races: {inconsistency_report['alive_races']}")
        
        if inconsistency_report['log']:
            print(f"\n  Recent inconsistencies:")
            for inc in inconsistency_report['log'][-5:]:
                print(f"    - {inc}")
        
        get_global_metrics().print_summary()
    
    # Save to file if specified
    if datafile is not None:
        with open(datafile, 'w') as f:
            f.write(f'Battle ended at t={t:.1f}s steps={step}. Winner: P{winner}\n')
            f.write(f'Simulation took {simulation_time:.2f}s wall time. Engine ticks: {engine.tick:.2f}\n')
            f.write('Events:\n')
            for event in engine.events:
                f.write(f'   {event}\n')
            
            # V1: Save network metrics
            if net_bridge:
                f.write('\n[V1 NETWORK INCONSISTENCY REPORT]\n')
                inconsistency_report = net_bridge.get_inconsistency_report()
                f.write(f'Total inconsistencies: {inconsistency_report["total_inconsistencies"]}\n')
                f.write(f'  Position races: {inconsistency_report["position_races"]}\n')
                f.write(f'  HP races: {inconsistency_report["hp_races"]}\n')
                f.write(f'  Alive races: {inconsistency_report["alive_races"]}\n')
                f.write('\nInconsistency log:\n')
                for inc in inconsistency_report['log']:
                    f.write(f'  {inc}\n')
                
                f.write('\n[V1 NETWORK METRICS]\n')
                metrics_summary = get_global_metrics().get_summary()
                f.write(f"Duration: {metrics_summary['duration_sec']}s\n")
                f.write(f"Messages sent: {metrics_summary['messages']['sent']}\n")
                f.write(f"Messages received: {metrics_summary['messages']['received']}\n")
                f.write(f"Avg latency: {metrics_summary['messages']['avg_latency_ms']:.2f}ms\n")
                f.write(f"Total race conditions: {metrics_summary['races']['total']}\n")
                f.write(f"Total state mismatches: {metrics_summary['mismatches']['total']}\n")
        
        print(f'\nBattle data successfully written to {datafile}')
    
    return winner, t, step, simulation_time


def main():
    parser = argparse.ArgumentParser(description='Battle simulation CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # run command
    run_parser = subparsers.add_parser('run', help='Run a battle scenario')
    run_parser.add_argument('scenario', help='Scenario to run (tiny_scenario, square_scenario, chevron_scenario, optimal_scenario, echelon_scenario)')
    run_parser.add_argument('AI1', nargs='?', default='DaftGeneral', help='First AI (default: DaftGeneral)')
    run_parser.add_argument('AI2', nargs='?', default='BrainDeadGeneral', help='Second AI (default: BrainDeadGeneral)')
    run_parser.add_argument('-t', action='store_true', help='Terminal/headless view (default: 2.5D PyGame)')
    run_parser.add_argument('-d', type=str, help='Data file to save results')
    run_parser.add_argument('--seed', type=int, help='Random seed')
    run_parser.add_argument('--net-enable', action='store_true', help='Enable P2P network integration for run command')
    run_parser.add_argument('--net-host', default='127.0.0.1', help='Local C node host for Python TCP client')
    run_parser.add_argument('--net-port', type=int, default=9001, help='Local C node port for Python TCP client')
    run_parser.add_argument('--net-local-player', type=int, choices=[1, 2], default=1, help='Player controlled by this process in network mode')

    # load command
    load_parser = subparsers.add_parser('load', help='Load a saved battle')
    load_parser.add_argument('savefile', help='Save file to load')

    # tourney command
    tourney_parser = subparsers.add_parser('tourney', help='Run a tournament')
    tourney_parser.add_argument('-G', nargs='+', default=['DaftGeneral', 'BrainDeadGeneral'], help='List of AIs')
    tourney_parser.add_argument('-S', nargs='+', default=['square_scenario'], help='List of scenarios')
    tourney_parser.add_argument('-N', type=int, default=10, help='Number of rounds per matchup')
    tourney_parser.add_argument('-na', action='store_true', help='Do not alternate positions')
    tourney_parser.add_argument('-d', type=str, help='Data file to save results')

    # plot command
    plot_parser = subparsers.add_parser('plot', help='Plot outcomes of a scenario with parameters')
    plot_parser.add_argument('AI', help='AI name (e.g., DAFT, BrainDead)')
    plot_parser.add_argument('plotter', help='Plotter type (e.g., PlotLanchester)')
    plot_parser.add_argument('scenario', help='Scenario name (e.g., Lanchester)')
    plot_parser.add_argument('units', nargs='+', help='Units to test in format: [Unit1,Unit2,...] or Unit1 Unit2 ...')
    plot_parser.add_argument('range_values', nargs='*', help='Range specification (e.g., range (1,100))')
    plot_parser.add_argument('-N', type=int, default=10, help='Number of rounds for each test')

    # view command (interactive PyGame)
    view_parser = subparsers.add_parser('view', help='View battle with interactive 2.5D/PyGame renderer')
    view_parser.add_argument('scenario', nargs='?', default='square_scenario', help='Scenario to view (square_scenario, chevron_scenario, optimal_scenario, echelon_scenario)')
    view_parser.add_argument('AI1', nargs='?', default='DaftGeneral', help='First AI')
    view_parser.add_argument('AI2', nargs='?', default='BrainDeadGeneral', help='Second AI')
    view_parser.add_argument('--seed', type=int, help='Random seed')

    args = parser.parse_args()

    # Handle run command
    if args.command == 'run':
        if args.seed is not None:
            random.seed(args.seed)
        
        print('Starting battle simulation...')
        engine = SimpleEngine(w=MAP_W, h=MAP_H)
        scenario_func = get_scenario(args.scenario)
        scenario_func(engine)
        
        AI1_class = get_ai_class(args.AI1)
        AI2_class = get_ai_class(args.AI2)
        generals = {
            1: AI1_class(1),
            2: AI2_class(2)
        }

        net_bridge: Optional[NetworkBridge] = None
        if args.net_enable:
            reset_metrics()  # V1: Reset metrics for this battle
            try:
                net_bridge = NetworkBridge(
                    host=args.net_host,
                    port=args.net_port,
                    local_player=args.net_local_player,
                )
                net_bridge.connect()
                generals = configure_network_generals(generals, net_bridge, args.net_local_player)
                print(
                    f"[NET] enabled: local_player={args.net_local_player}, "
                    f"node={args.net_host}:{args.net_port}"
                )
            except Exception as exc:
                print(f"[NET] failed to initialize network mode: {exc}")
                print("[NET] continuing in offline mode.")
                net_bridge = None
        
        # If -t flag: run with terminal visualization
        if args.t:
            current_view = 'terminal'
            while True:
                if current_view == 'terminal':
                    print('Running with terminal map visualization...')
                    try:
                        from TerminalRenderer import TerminalRenderer
                        renderer = TerminalRenderer(engine, generals, net_bridge=net_bridge)
                        result = renderer.run()
                        
                        # Check if user pressed F9 to switch to PyGame
                        if result == 'switch_pygame':
                            print('Switching to 2.5D PyGame view...')
                            current_view = 'pygame'
                            continue
                        else:
                            break
                    except ImportError as e:
                        print(f"Terminal view not available: {e}")
                        print("Falling back to headless mode...")
                        run_headless_battle(engine, generals, datafile=args.d)
                        break
                    except Exception as e:
                        print(f"Error running terminal viewer: {e}")
                        print("Falling back to headless mode...")
                        run_headless_battle(engine, generals, datafile=args.d)
                        break
                
                elif current_view == 'pygame':
                    try:
                        import pygame
                        from PyGameRenderer import PygameRenderer
                        pygame_renderer = PygameRenderer(engine, generals, net_bridge=net_bridge)
                        result = pygame_renderer.run()
                        
                        # Check if user pressed F9 to switch back to terminal
                        if result == 'switch_terminal':
                            print('Switching back to terminal view...')
                            current_view = 'terminal'
                            continue
                        else:
                            break
                    except ImportError:
                        print("PyGame not available")
                        break
                    except Exception as e:
                        print(f"Error in PyGame viewer: {e}")
                        break
            
            # Save data file if specified
            if args.d is not None:
                winner = pygame_renderer.winner if 'pygame_renderer' in locals() and hasattr(pygame_renderer, 'winner') else None
                with open(args.d, 'w') as f:
                    f.write(f'Battle data from {current_view} view\n')
                    f.write(f'Engine ticks: {engine.tick:.2f}\n')
                    if winner:
                        if winner == 1:
                            f.write('Winner: PLAYER 1 (RED)\n')
                        elif winner == 2:
                            f.write('Winner: PLAYER 2 (BLUE)\n')
                    f.write('Events:\n')
                    for event in engine.events:
                        f.write(f'   {event}\n')

                    if net_bridge is not None:
                        f.write('\n[V1 NETWORK INCONSISTENCY REPORT]\n')
                        inconsistency_report = net_bridge.get_inconsistency_report()
                        f.write(f'Total inconsistencies: {inconsistency_report["total_inconsistencies"]}\n')
                        f.write(f'  Position races: {inconsistency_report["position_races"]}\n')
                        f.write(f'  HP races: {inconsistency_report["hp_races"]}\n')
                        f.write(f'  Alive races: {inconsistency_report["alive_races"]}\n')
                        f.write('\nInconsistency log:\n')
                        for inc in inconsistency_report['log']:
                            f.write(f'  {inc}\n')

                        f.write('\n[V1 NETWORK METRICS]\n')
                        metrics_summary = get_global_metrics().get_summary()
                        f.write(f"Duration: {metrics_summary['duration_sec']}s\n")
                        f.write(f"Messages sent: {metrics_summary['messages']['sent']}\n")
                        f.write(f"Messages received: {metrics_summary['messages']['received']}\n")
                        f.write(f"Avg latency: {metrics_summary['messages']['avg_latency_ms']:.2f}ms\n")
                        f.write(f"Total race conditions: {metrics_summary['races']['total']}\n")
                        f.write(f"Total state mismatches: {metrics_summary['mismatches']['total']}\n")
                print(f'Battle data saved to {args.d}')
        else:
            # Default: show 2.5D PyGame visualization
            current_view = 'pygame'
            while True:
                if current_view == 'pygame':
                    print('Opening 2.5D map viewer...')
                    try:
                        import pygame
                        from PyGameRenderer import PygameRenderer
                        renderer = PygameRenderer(engine, generals, net_bridge=net_bridge)
                        result = renderer.run()
                        
                        # Check if user pressed F9 to switch to terminal
                        if result == 'switch_terminal':
                            print('Switching to terminal view...')
                            current_view = 'terminal'
                            continue
                        else:
                            break
                    except ImportError:
                        print("PyGame not available. Install with: pip install pygame")
                        print("Falling back to terminal view...")
                        current_view = 'terminal'
                        continue
                    except Exception as e:
                        print(f"Error running PyGame viewer: {e}")
                        print("Falling back to terminal view...")
                        current_view = 'terminal'
                        continue
                
                elif current_view == 'terminal':
                    try:
                        from TerminalRenderer import TerminalRenderer
                        renderer = TerminalRenderer(engine, generals)
                        result = renderer.run()
                        
                        # Check if user pressed F9 to switch back to PyGame
                        if result == 'switch_pygame':
                            print('Switching back to 2.5D PyGame view...')
                            current_view = 'pygame'
                            continue
                        else:
                            break
                    except ImportError:
                        print("Terminal view not available")
                        break
                    except Exception as e:
                        print(f"Error in terminal viewer: {e}")
                        import traceback
                        traceback.print_exc()
                        break
            
            # Save data file if specified
            if args.d is not None:
                winner = renderer.winner if 'renderer' in locals() and hasattr(renderer, 'winner') else None
                with open(args.d, 'w') as f:
                    f.write(f'Battle data from {current_view} view\n')
                    f.write(f'Engine ticks: {engine.tick:.2f}\n')
                    if winner:
                        if winner == 1:
                            f.write('Winner: PLAYER 1 (RED)\n')
                        elif winner == 2:
                            f.write('Winner: PLAYER 2 (BLUE)\n')
                    f.write('Events:\n')
                    for event in engine.events:
                        f.write(f'   {event}\n')

                    if net_bridge is not None:
                        f.write('\n[V1 NETWORK INCONSISTENCY REPORT]\n')
                        inconsistency_report = net_bridge.get_inconsistency_report()
                        f.write(f'Total inconsistencies: {inconsistency_report["total_inconsistencies"]}\n')
                        f.write(f'  Position races: {inconsistency_report["position_races"]}\n')
                        f.write(f'  HP races: {inconsistency_report["hp_races"]}\n')
                        f.write(f'  Alive races: {inconsistency_report["alive_races"]}\n')
                        f.write('\nInconsistency log:\n')
                        for inc in inconsistency_report['log']:
                            f.write(f'  {inc}\n')

                        f.write('\n[V1 NETWORK METRICS]\n')
                        metrics_summary = get_global_metrics().get_summary()
                        f.write(f"Duration: {metrics_summary['duration_sec']}s\n")
                        f.write(f"Messages sent: {metrics_summary['messages']['sent']}\n")
                        f.write(f"Messages received: {metrics_summary['messages']['received']}\n")
                        f.write(f"Avg latency: {metrics_summary['messages']['avg_latency_ms']:.2f}ms\n")
                        f.write(f"Total race conditions: {metrics_summary['races']['total']}\n")
                        f.write(f"Total state mismatches: {metrics_summary['mismatches']['total']}\n")
                print(f'Battle data saved to {args.d}')

                if net_bridge is not None:
                    net_bridge.close()

    # Handle load command
    elif args.command == 'load':
        print(f"Loading battle from {args.savefile}...")
        try:
            from GameState import GameStateManager
            state_manager = GameStateManager()
            
            # Try to load the file
            state = state_manager.quick_load(args.savefile)
            
            if state is None:
                print(f"Error: Save file '{args.savefile}' not found in saves/ directory")
            else:
                # Create engine and restore state
                engine = SimpleEngine(w=state['engine']['w'], h=state['engine']['h'])
                state_manager.restore_engine(state, engine)
                generals = state_manager.restore_generals(state)
                
                print(f"Battle loaded successfully! Engine tick: {engine.tick:.2f}")
                print(f"Units: {len(engine.units)}")
                print(f"Opening 2.5D map viewer...\n")
                
                # Launch with PyGame viewer
                current_view = 'pygame'
                while True:
                    if current_view == 'pygame':
                        try:
                            import pygame
                            from PyGameRenderer import PygameRenderer
                            renderer = PygameRenderer(engine, generals)
                            result = renderer.run()
                            
                            if result == 'switch_terminal':
                                print('Switching to terminal view...')
                                current_view = 'terminal'
                                continue
                            else:
                                break
                        except ImportError:
                            print("PyGame not available. Install with: pip install pygame")
                            break
                        except Exception as e:
                            print(f"Error running PyGame viewer: {e}")
                            break
                    
                    elif current_view == 'terminal':
                        try:
                            from TerminalRenderer import TerminalRenderer
                            renderer = TerminalRenderer(engine, generals)
                            result = renderer.run()
                            
                            if result == 'switch_pygame':
                                print('Switching back to 2.5D PyGame view...')
                                current_view = 'pygame'
                                continue
                            else:
                                break
                        except ImportError:
                            print("Terminal view not available")
                            break
                        except Exception as e:
                            print(f"Error in terminal viewer: {e}")
                            break
        except Exception as e:
            print(f"Error loading battle: {e}")
            import traceback
            traceback.print_exc()

    # Handle tourney command
    elif args.command == 'tourney':
        print(f"Running tournament with {len(args.G)} AIs, {len(args.S)} scenarios, {args.N} rounds each")
        print(f"AIs: {', '.join(args.G)}")
        print(f"Scenarios: {', '.join(args.S)}")
        print(f"Alternate positions: {not args.na}")
        
        results = {}
        total_matches = 0
        
        for scenario_name in args.S:
            for i, ai1 in enumerate(args.G):
                for ai2 in args.G[i+1:]:
                    matchup = f"{ai1} vs {ai2} ({scenario_name})"
                    results[matchup] = {'ai1_wins': 0, 'ai2_wins': 0, 'draws': 0}
                    
                    for round_num in range(args.N):
                        engine = SimpleEngine(w=MAP_W, h=MAP_H)
                        scenario_func = get_scenario(scenario_name)
                        scenario_func(engine)
                        
                        # Create generals
                        if args.na or round_num % 2 == 0:
                            generals = {
                                1: get_ai_class(ai1)(1),
                                2: get_ai_class(ai2)(2)
                            }
                            p1_ai, p2_ai = ai1, ai2
                        else:
                            generals = {
                                1: get_ai_class(ai2)(1),
                                2: get_ai_class(ai1)(2)
                            }
                            p1_ai, p2_ai = ai2, ai1
                        
                        winner, t, step, sim_time = run_battle(engine, generals, datafile=None)
                        
                        if winner == 0:
                            results[matchup]['draws'] += 1
                        elif winner == 1:
                            if p1_ai == ai1:
                                results[matchup]['ai1_wins'] += 1
                            else:
                                results[matchup]['ai2_wins'] += 1
                        else:
                            if p2_ai == ai1:
                                results[matchup]['ai1_wins'] += 1
                            else:
                                results[matchup]['ai2_wins'] += 1
                        
                        total_matches += 1
        
        print(f"\nTournament Results ({total_matches} matches):")
        for matchup, stats in results.items():
            print(f"{matchup}: {stats['ai1_wins']}-{stats['ai2_wins']}-{stats['draws']}")
        
        # Save to file if specified
        if args.d is not None:
            with open(args.d, 'w') as f:
                f.write(f"Tournament Results ({total_matches} matches):\n")
                for matchup, stats in results.items():
                    f.write(f"{matchup}: {stats['ai1_wins']}-{stats['ai2_wins']}-{stats['draws']}\n")
            print(f"\nTournament results saved to {args.d}")

    # Handle plot command
    elif args.command == 'plot':
        # The units and range_values get combined when parsed, we need to separate them
        # Look for "range" keyword in the arguments
        all_args = args.units + (args.range_values if args.range_values else [])
        
        # Find where "range" starts
        range_start = -1
        unit_list = []
        for i, arg in enumerate(all_args):
            if 'range' in arg.lower():
                range_start = i
                break
            unit_list.append(arg)
        
        if range_start == -1:
            range_str = ''
            unit_list = all_args
        else:
            range_str = ' '.join(all_args[range_start:])
        
        print(f"Plotting {args.AI} with {args.plotter} on scenario {args.scenario}")
        print(f"Units: {', '.join(unit_list)}")
        if range_str:
            print(f"Range: {range_str}")
        print(f"Rounds per test: {args.N}\n")
        
        try:
            if args.plotter == 'PlotLanchester':
                print("Validation Scientifique : Génération du graphique Lanchester (PNG)...")
                generate_lanchester_plot() # Appelle ton fichier battle_plot.py
                return
            import re
            
            # Try different patterns
            range_match = re.search(r'range\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)', range_str)
            if not range_match:
                # Try pattern without parentheses: "range 1 100"
                range_match = re.search(r'range\s+(\d+)\s+(\d+)', range_str)
            
            if not range_match:
                print("Error: Range must be specified as 'range(1,100)' or 'range (1, 100)'")
                print(f"Got: {range_str}")
            else:
                start_val = int(range_match.group(1))
                end_val = int(range_match.group(2))
                
                # Parse unit list from format like "[Knight,Crossbow]" or "Knight Crossbow"
                unit_names = []
                for unit_spec in unit_list:
                    # Remove brackets if present
                    unit_spec = unit_spec.strip('[]')
                    # Split by comma if comma-separated
                    units_in_spec = [u.strip() for u in unit_spec.split(',')]
                    unit_names.extend(units_in_spec)
                
                print(f"Testing {len(unit_names)} unit(s) from {start_val} to {end_val} per unit")
                print(f"Total test combinations: {(end_val - start_val + 1)}")
                print()
                
                # Prepare results
                results = []
                test_count = 0
                
                # Test each count level
                for count in range(start_val, end_val + 1):
                    print(f"Testing with {count} units of each type...", end='', flush=True)
                    win_count = 0
                    
                    # Run N rounds at this unit count
                    for round_num in range(args.N):
                        # Create engine and scenario
                        engine = SimpleEngine(w=MAP_W, h=MAP_H)
                        scenario_func = get_scenario(args.scenario)
                        scenario_func(engine)
                        
                        # Modify unit counts in the scenario
                        # Remove existing units and recreate with specified count
                        engine.units.clear()
                        engine.units_by_id.clear()
                        engine.next_unit_id = 1
                        
                        # Add player 1 units
                        for i in range(count):
                            from Units import Unit
                            for j, unit_name in enumerate(unit_names):
                                u = Unit(id=engine.next_unit_id, player=1, x=10+i%5, y=10+j, unit_type=unit_name)
                                engine.units.append(u)
                                engine.units_by_id[u.id] = u
                                engine.next_unit_id += 1
                        
                        # Add player 2 units (opponent)
                        for i in range(count):
                            for j, unit_name in enumerate(unit_names):
                                u = Unit(id=engine.next_unit_id, player=2, x=MAP_W-10-i%5, y=MAP_H-10-j, unit_type=unit_name)
                                engine.units.append(u)
                                engine.units_by_id[u.id] = u
                                engine.next_unit_id += 1
                        
                        # Run battle
                        t = 0.0
                        dt = 0.2
                        max_ticks = 180.0
                        AI_class = get_ai_class(args.AI)
                        generals = {1: AI_class(1), 2: AI_class(2)}
                        
                        while t < max_ticks:
                            engine.step(dt, generals)
                            t += dt
                            p1 = engine.get_units_for_player(1)
                            p2 = engine.get_units_for_player(2)
                            if not p1 or not p2:
                                break
                        
                        # Check winner
                        p1_alive = len(engine.get_units_for_player(1))
                        p2_alive = len(engine.get_units_for_player(2))
                        
                        if p1_alive > 0:
                            win_count += 1
                    
                    win_rate = (win_count / args.N) * 100
                    results.append((count, win_rate))
                    print(f" {win_count}/{args.N} wins ({win_rate:.1f}%)")
                    test_count += 1
                
                # Display results
                print("\n" + "="*50)
                print("PLOT RESULTS")
                print("="*50)
                print(f"{'Unit Count':<15} {'Win Rate':<15} {'Graph':<20}")
                print("-"*50)
                
                for count, win_rate in results:
                    bar_length = int(win_rate / 5)  # Scale to 20 chars max
                    bar = '█' * bar_length + '░' * (20 - bar_length)
                    print(f"{count:<15} {win_rate:>6.1f}%       {bar}")
                
                print("="*50)
                print(f"Tested {test_count} combinations with {args.N} rounds each")
                
        except Exception as e:
            print(f"Error in plot: {e}")
            import traceback
            traceback.print_exc()

    # Handle view command
    elif args.command == 'view':
        if args.seed is not None:
            random.seed(args.seed)
        
        print('Starting interactive battle simulation with PyGame viewer...')
        engine = SimpleEngine(w=MAP_W, h=MAP_H)
        scenario_func = get_scenario(args.scenario)
        scenario_func(engine)
        
        AI1_class = get_ai_class(args.AI1)
        AI2_class = get_ai_class(args.AI2)
        generals = {
            1: AI1_class(1),
            2: AI2_class(2)
        }
        
        try:
            import pygame
            from PyGameRenderer import PygameRenderer
            renderer = PygameRenderer(engine, generals)
            renderer.run()
        except ImportError:
            print("PyGame not available. Install with: pip install pygame")
        except Exception as e:
            print(f"Error running PyGame viewer: {e}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
