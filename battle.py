#!/usr/bin/env python
"""
Battle CLI - Entry point with mode selection

Usage (interactive menu):
    python battle.py

Usage (direct, backward-compatible):
    battle run <scenario> [AI1] [AI2] [-t] [-d DATAFILE] [--seed SEED]
    battle load <savefile>
    battle tourney [-G AI1 AI2...] [-S SCENARIO...] [-N ROUNDS]
    battle plot <AI> <plotter> <scenario> <units...>
"""

import sys
import os
import importlib.util

script_dir = os.path.dirname(os.path.abspath(__file__))
finalcode_dir = os.path.join(script_dir, 'age', 'FinalCode')
if os.path.exists(finalcode_dir):
    sys.path.insert(0, finalcode_dir)
else:
    sys.path.insert(0, script_dir)

# Windows : _curses n'est pas fourni par CPython. windows-curses l'enregistre
# mais doit être importé avant curses. Si absent, on injecte un stub minimal.
try:
    import windows_curses  # noqa: F401  — enregistre _curses sur Windows
except ModuleNotFoundError:
    pass
try:
    import curses  # noqa: F401
except ModuleNotFoundError:
    import types as _types
    _curses_stub = _types.ModuleType("curses")
    _curses_stub.wrapper     = lambda fn, *a, **kw: fn(None, *a, **kw)
    _curses_stub.initscr     = lambda: None
    _curses_stub.endwin      = lambda: None
    _curses_stub.curs_set    = lambda n: None
    _curses_stub.noecho      = lambda: None
    _curses_stub.cbreak      = lambda: None
    _curses_stub.start_color = lambda: None
    _curses_stub.has_colors  = lambda: False
    _curses_stub.color_pair  = lambda n: 0
    _curses_stub.init_pair   = lambda *a: None
    _curses_stub.KEY_UP      = 259
    _curses_stub.KEY_DOWN    = 258
    _curses_stub.KEY_LEFT    = 260
    _curses_stub.KEY_RIGHT   = 261
    sys.modules["curses"] = _curses_stub


SCENARIOS = [
    'square_scenario',
    'chevron_scenario',
    'optimal_scenario',
    'echelon_scenario',
    'tiny_scenario',
]

AIS = [
    'DaftGeneral',
    'BrainDeadGeneral',
    'New_General_1',
    'New_General_2',
    'New_General_3',
    'GenghisKhanPrimeGeneral',
]


def _show_menu():
    print("")
    print("  ╔══════════════════════════════╗")
    print("  ║     P2P-MedievAI Launcher    ║")
    print("  ╠══════════════════════════════╣")
    print("  ║  1. battle  - Lancer le jeu  ║")
    print("  ║  2. chat    - Mode réseau    ║")
    print("  ╚══════════════════════════════╝")
    print("")
    while True:
        choice = input("  Choisissez un mode (battle/chat) : ").strip().lower()
        if choice in ('1', 'battle', 'b'):
            return 'battle'
        if choice in ('2', 'chat', 'c'):
            return 'chat'
        print(f"  Choix invalide '{choice}'. Tapez 'battle' ou 'chat'.")


def _launch_battle():
    print("")
    print(f"  Scénarios disponibles : {', '.join(SCENARIOS)}")
    scenario = input("  Scénario         [square_scenario] : ").strip() or 'square_scenario'
    print(f"  IAs disponibles  : {', '.join(AIS)}")
    ai1 = input("  IA Joueur 1      [DaftGeneral]      : ").strip() or 'DaftGeneral'
    ai2 = input("  IA Joueur 2      [BrainDeadGeneral] : ").strip() or 'BrainDeadGeneral'

    sys.argv = [sys.argv[0], 'run', scenario, ai1, ai2]

    from Main import main
    main()


def _launch_chat():
    print("")
    host = input("  Host  [127.0.0.1] : ").strip() or '127.0.0.1'
    port  = input("  Port  [9000]      : ").strip() or '9000'
    name  = input("  Nom   [player1]   : ").strip() or 'player1'

    sys.argv = [sys.argv[0], '--host', host, '--port', port, '--name', name]

    chat_path = os.path.join(finalcode_dir, 'test_tcp_client.py')
    spec = importlib.util.spec_from_file_location('test_tcp_client', chat_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Arguments fournis directement → comportement original intact
        from Main import main
        main()
    else:
        mode = _show_menu()
        if mode == 'battle':
            _launch_battle()
        else:
            _launch_chat()
