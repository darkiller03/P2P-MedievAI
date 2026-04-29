#!/usr/bin/env python3
"""
CLI Entry Point for MedievAIl Battle Simulator.
"""

import argparse
import pickle
import sys
import os

from model.game import Game
from model.map import BattleMap
from .ai import CaptainBraindead, MajorDaft, AssasinJack, PredictEinstein
from .smartAI import GeneralStrategus
from model.scenarios import (
    scenario_simple_vs_braindead,
    scenario_small_terminal,
    scenario_lanchester,
    scenario_bataille_colline,
    scenario_deux_camps_eleves,
    scenario_deux_camps_eleves,
    scenario_siege_chateau,
    scenario_wonder_duel,
)
AVAILABLE_AIS = {
    "Braindead": CaptainBraindead,
    "Daft": MajorDaft,
    "GeneralStrategus": GeneralStrategus,
    "AssasinJack": AssasinJack,
    "PredictEinstein": PredictEinstein,
}

AVAILABLE_SCENARIOS = {
    "Scenario_Standard": scenario_small_terminal,
    "Scenario_Dur": scenario_simple_vs_braindead,
    "Bataille_Colline": scenario_bataille_colline,
    "Deux_Camps": scenario_deux_camps_eleves,
    "Deux_Camps": scenario_deux_camps_eleves,
    "Siege_Chateau": scenario_siege_chateau,
    "Wonder_Duel": scenario_wonder_duel,
}


def run_battle(scenario_name, ai1_name, ai2_name, terminal_mode=False, datafile=None, savefile=None):
    if scenario_name in AVAILABLE_SCENARIOS:
        base_game = AVAILABLE_SCENARIOS[scenario_name]()
    else:
        try:
            base_game = eval(scenario_name)
        except Exception as e:
            print(f"Erreur : Scénario '{scenario_name}' inconnu ou invalide. {e}")
            return None

    if ai1_name not in AVAILABLE_AIS:
        print(f"Erreur : IA '{ai1_name}' inconnue. Disponibles : {list(AVAILABLE_AIS.keys())}")
        return None
    if ai2_name not in AVAILABLE_AIS:
        print(f"Erreur : IA '{ai2_name}' inconnue. Disponibles : {list(AVAILABLE_AIS.keys())}")
        return None

    controllers = {
        "A": AVAILABLE_AIS[ai1_name]("A"),
        "B": AVAILABLE_AIS[ai2_name]("B"),
    }
    base_game.controllers = controllers

    if terminal_mode:
        from view.terminal_view import TerminalView
        view = TerminalView(base_game)
        view.start()
    else:
        import pygame
        from view.views import GUI

        pygame.init()
        screen = pygame.display.set_mode((1024, 768), pygame.RESIZABLE)
        pygame.display.set_caption(f"Battle: {ai1_name} vs {ai2_name}")
        clock = pygame.time.Clock()
        gui = GUI(base_game, 1024, 768)

        auto_play = True
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                gui.handle_events(event)

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        auto_play = not auto_play
                    if event.key == pygame.K_SPACE:
                        base_game.step(dt=0.1)
                    if event.key == pygame.K_F9:
                        pygame.quit()
                        from view.terminal_view import TerminalView
                        view = TerminalView(base_game)
                        view.start()
                        return base_game

            if not base_game.is_finished() and auto_play:
                base_game.step(dt=0.05)

            gui.handle_input()
            gui.draw(screen)
            pygame.display.flip()
            clock.tick(30)

            if base_game.is_finished():
                pygame.time.wait(2000)
                running = False

        pygame.quit()

    if datafile:
        summary = base_game.get_battle_summary()
        with open(datafile, "w", encoding="utf-8") as f:
            f.write(str(summary))
        print(f"Données écrites dans {datafile}")

    if savefile:
        with open(savefile, "wb") as f:
            pickle.dump(base_game, f)
        print(f"État du jeu sauvegardé dans {savefile}")

    return base_game


def load_game(savefile):
    if not os.path.exists(savefile):
        print(f"Erreur : Fichier '{savefile}' introuvable.")
        return

    with open(savefile, "rb") as f:
        game = pickle.load(f)

    print(f"Partie chargée depuis {savefile}")
    print(f"Temps simulé : {game.time:.1f}s, Unités en vie : {len(game.alive_units())}")

    import pygame
    from view.views import GUI

    pygame.init()
    screen = pygame.display.set_mode((1024, 768), pygame.RESIZABLE)
    pygame.display.set_caption("Partie chargée")
    clock = pygame.time.Clock()
    gui = GUI(game, 1024, 768)

    auto_play = False
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            gui.handle_events(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    auto_play = not auto_play

        if not game.is_finished() and auto_play:
            game.step(dt=0.1)

        gui.handle_input()
        gui.draw(screen)
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


def run_tournament(generals, scenarios, rounds=10, alternate=True):
    from .tournament import Tournament

    if not generals:
        generals = list(AVAILABLE_AIS.keys())
    if not scenarios:
        scenarios = list(AVAILABLE_SCENARIOS.keys())

    print(f"\n{'='*50}")
    print(f"TOURNOI AUTOMATIQUE")
    print(f"Généraux : {generals}")
    print(f"Scénarios : {scenarios}")
    print(f"Rounds par matchup : {rounds}")
    print(f"Alternance des positions : {alternate}")
    print(f"{'='*50}\n")

    t = Tournament(generals, scenarios, rounds=rounds)
    t.run()


def run_plot(ai_name, plotter_name, scenario_expr, range_expr=None, rounds=10):
    from .graphes_lanchester import (
        plot_loi_carree,
        plot_comparaison_lanchester,
    )

    plotter_lower = plotter_name.lower()

    if plotter_lower in ["plotlanchester", "lanchester", "squarelaw"]:
        try:
            if "[" in scenario_expr and "]" in scenario_expr:
                bracket_content = scenario_expr.split("[")[1].split("]")[0]
                unit_types = [u.strip().strip('"').strip("'").lower() for u in bracket_content.split(",")]
            else:
                unit_types = ["knight"]
        except Exception as e:
            print(f"Erreur parsing types d'unités : {e}")
            print("Format attendu : Lanchester [knight,crossbowman] ou [Knight,Pikeman]")
            unit_types = ["knight"]

        if range_expr:
            try:
                values = list(eval(range_expr))
                max_n = max(values)
            except Exception as e:
                print(f"Erreur évaluation range : {e}")
                max_n = 20
        else:
            max_n = 20

        print(f"\n{'='*50}")
        print(f"VÉRIFICATION LOI CARRÉE DE LANCHESTER")
        print(f"Types d'unités : {unit_types}")
        print(f"N max : {max_n}")
        print(f"{'='*50}\n")

        plot_loi_carree(unit_types, max_n=max_n, save_plot=True)

    elif plotter_lower in ["comparelanchester", "compare", "verify"]:
        scenario_func = None
        scenario_name = scenario_expr

        if scenario_expr in AVAILABLE_SCENARIOS:
            scenario_func = AVAILABLE_SCENARIOS[scenario_expr]
            scenario_name = scenario_expr
        elif scenario_expr.lower() == "scenario_standard":
            from model.scenarios import scenario_small_terminal
            scenario_func = scenario_small_terminal
            scenario_name = "Scenario Standard"
        elif scenario_expr.lower() == "scenario_terminal":
            from model.scenarios import scenario_small_terminal
            scenario_func = scenario_small_terminal
            scenario_name = "Scenario Terminal"
        else:
            print(f"Erreur : Scénario '{scenario_expr}' inconnu.")
            print(f"Scénarios disponibles : {list(AVAILABLE_SCENARIOS.keys())}")
            return

        print(f"\n{'='*50}")
        print(f"COMPARAISON LANCHESTER VS SIMULATION RÉELLE")
        print(f"Scénario : {scenario_name}")
        print(f"{'='*50}\n")

        plot_comparaison_lanchester(scenario_func, scenario_name, save_plot=True)

    else:
        print(f"Erreur : Plotter '{plotter_name}' inconnu.")
        print("Plotters disponibles :")
        print("  - PlotLanchester / SquareLaw : Vérification loi carrée")
        print("  - CompareLanchester / Compare : Comparaison théorie vs réel")
        print("\nExemples :")
        print('  battle plot DAFT PlotLanchester "Lanchester [knight,crossbowman]" "range(1,20)"')
        print('  battle plot DAFT CompareLanchester Scenario_Standard')


def main():
    parser = argparse.ArgumentParser(
        prog="battle",
        description="MedievAIl Battle Simulator - CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  battle run Scenario_Standard Daft Braindead -t
  battle run Scenario_Dur Daft GeneralStrategus -s final_state.pkl
  battle load quicksave.pkl
  battle tourney -G Daft Braindead GeneralStrategus -N 5
  battle plot DAFT PlotLanchester "Lanchester [knight,crossbowman]" "range(1,20)"
  battle plot DAFT CompareLanchester Scenario_Standard
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")

    # --- RUN ---
    run_parser = subparsers.add_parser("run", help="Lancer une bataille")
    run_parser.add_argument("scenario", help="Nom du scénario")
    run_parser.add_argument("ai1", help="IA du joueur A")
    run_parser.add_argument("ai2", help="IA du joueur B")
    run_parser.add_argument("-t", "--terminal", action="store_true", help="Mode terminal")
    run_parser.add_argument("-d", "--datafile", help="Fichier de données de sortie (résumé texte)")
    run_parser.add_argument("-s", "--savefile", help="Fichier de sauvegarde (.pkl) pour l'état complet")

    # --- LOAD ---
    load_parser = subparsers.add_parser("load", help="Charger une sauvegarde")
    load_parser.add_argument("savefile", help="Fichier de sauvegarde (.pkl)")

    # --- TOURNEY ---
    tourney_parser = subparsers.add_parser("tourney", help="Lancer un tournoi")
    tourney_parser.add_argument("-G", "--generals", nargs="+", help="Liste des IA")
    tourney_parser.add_argument("-S", "--scenarios", nargs="+", help="Liste des scénarios")
    tourney_parser.add_argument("-N", "--rounds", type=int, default=10, help="Rounds par matchup")
    tourney_parser.add_argument("-na", "--no-alternate", action="store_true", help="Ne pas alterner les positions")

    # --- PLOT ---
    plot_parser = subparsers.add_parser("plot", help="Générer un graphique Lanchester")
    plot_parser.add_argument("ai", help="IA à utiliser")
    plot_parser.add_argument("plotter", help="Type de graphique (PlotLanchester, CompareLanchester, SquareLaw)")
    plot_parser.add_argument("scenario", help="Expression du scénario ou [unit_types]")
    plot_parser.add_argument("range", nargs="?", default=None, help="Range des valeurs (ex: range(1,20)) - optionnel pour CompareLanchester")
    plot_parser.add_argument("-N", "--rounds", type=int, default=10, help="Répétitions")

    args = parser.parse_args()

    if args.command == "run":
        run_battle(args.scenario, args.ai1, args.ai2, args.terminal, args.datafile, args.savefile)

    elif args.command == "load":
        load_game(args.savefile)

    elif args.command == "tourney":
        run_tournament(
            args.generals,
            args.scenarios,
            args.rounds,
            not args.no_alternate
        )

    elif args.command == "plot":
        run_plot(args.ai, args.plotter, args.scenario, args.range, args.rounds)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
