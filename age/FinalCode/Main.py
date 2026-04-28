import argparse
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
from network_integration import NetworkIntegrator, OwnershipTracker


class PassiveGeneral:
    """General used for remote-controlled players in network mode."""

    def __init__(self, player: int):
        self.player = player

    def give_orders(self, engine: SimpleEngine):
        _ = engine


class NetworkBridgeV2:
    """
    V2 Network bridge with complete ownership workflow.
    
    Phases:
    1) Request: local player requests ownership of remote unit
    2) Verify: remote owner checks if action is valid
    3) Grant: remote owner grants ownership with state snapshot
    4) Execute: local player performs verified action
    5) Publish: all players receive updated state
    """

    def __init__(self, host: str, port: int, local_player: int):
        self.client = P2PClient(host=host, port=port)
        self.local_player = local_player
        self.ownership = OwnershipTracker(local_player=local_player)
        self.integrator: Optional[NetworkIntegrator] = None
        self._last_processed_tick: Optional[float] = None
        self._last_sent_positions: Dict[int, Tuple[float, float]] = {}
        self._last_sent_targets: Dict[int, Optional[int]] = {}
        self._init_integrator = False

    def connect(self) -> None:
        self.client.connect()
        self.client.start_receiver_thread()
        self.client.send_message(f"HELLO|python|player{self.local_player}")

    def close(self) -> None:
        self.client.close()
    
    def _ensure_integrator(self, engine: SimpleEngine) -> None:
        """Lazy-init integrator once we have engine."""
        if not self._init_integrator:
            self.integrator = NetworkIntegrator(
                engine=engine,
                client=self.client,
                ownership=self.ownership,
                local_player=self.local_player
            )
            self._init_integrator = True

    def integrate_network(self, engine: SimpleEngine) -> None:
        """Process one tick of network messages."""
        self._ensure_integrator(engine)
        
        if self._last_processed_tick == engine.tick:
            return

        self.integrator.integrate_network()
        self._last_processed_tick = engine.tick

    def send_ai_action(self, action: Dict) -> None:
        """Send action with ownership verification."""
        self.integrator.send_action_with_ownership(action)

    def publish_local_actions(self, engine: SimpleEngine) -> None:
        """Publish state of local player's units."""
        if not self.integrator:
            return
        
        for u in engine.get_units_for_player(self.local_player):
            # Only publish if we own it
            if self.ownership.can_modify_local(u.id):
                self.integrator.publish_unit_state(u.id)
                
                prev_pos = self._last_sent_positions.get(u.id)
                current_pos = (round(u.x, 2), round(u.y, 2))
                if prev_pos != current_pos:
                    self.client.send_message(f"MOVE|{u.id}|{current_pos[0]}|{current_pos[1]}")
                    self._last_sent_positions[u.id] = current_pos

                prev_target = self._last_sent_targets.get(u.id)
                if u.target_id is not None and prev_target != u.target_id:
                    self.client.send_message(f"ATTACK|{u.id}|{u.target_id}")
                    self._last_sent_targets[u.id] = u.target_id


class NetworkedGeneral:
    """Wraps a local AI general and synchronizes with the network each tick."""

    def __init__(self, wrapped_general, bridge: NetworkBridgeV2):
        self.wrapped_general = wrapped_general
        self.bridge = bridge

    def give_orders(self, engine: SimpleEngine):
        self.wrapped_general.give_orders(engine)


def configure_network_generals(
    generals: Dict[int, object],
    bridge: NetworkBridgeV2,
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
            print(f"[NET] Processed incoming messages at step {step}")
        
        engine.step(dt, generals)
        t += dt
        step += 1
        
        # AFTER step: send local unit actions to network
        if net_bridge:
            net_bridge.publish_local_actions(engine)
            print(f"[NET] Published local actions at step {step}")
        
        p1 = engine.get_units_for_player(1)
        p2 = engine.get_units_for_player(2)
        if not p1 or not p2:
            winner = 2 if p2 else (1 if p1 else 0)
            break
    else:
        winner = 0  # Draw
    
    simulation_time = time.time() - start
    
    # Print results
    print(f"Battle ended at t={t:.1f}s steps={step}. Winner: P{winner}")
    print(f"Simulation took {simulation_time:.2f}s wall time. Engine ticks: {engine.tick:.2f}")
    print("Events:")
    for e in engine.events[-20:]:
        print("  ", e)
    
    # Save to file if specified
    if datafile is not None:
        with open(datafile, 'w') as f:
            f.write(f'Battle ended at t={t:.1f}s steps={step}. Winner: P{winner}\n')
            f.write(f'Simulation took {simulation_time:.2f}s wall time. Engine ticks: {engine.tick:.2f}\n')
            f.write('Events:\n')
            for event in engine.events:
                f.write(f'   {event}\n')
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

        net_bridge: Optional[NetworkBridgeV2] = None
        if args.net_enable:
            try:
                net_bridge = NetworkBridgeV2(
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
