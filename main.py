# main.py

import os
import time

from model.game import Game
from model.scenarios import scenario_simple_vs_braindead  # on importe notre scénario
from presenter.smartAI import GeneralStrategus


TEAM_INFO = {
    "A": {"name": "Kingdom of the North", "color": "Bleu", "ia": "MajorDaft (agressive)"},
    "B": {"name": "Empire of the South", "color": "Rouge", "ia": "Captain BRAINDEAD (statique)"},
    "C": {"name": "Smart Alliance", "color": "Vert", "ia": "GeneralStrategus (intelligente)"},
    "D": {"name": "The Ripper Coven", "color": "Jaune", "ia": "AssasinJack (intelligente)"},
    "E": {"name": "Soothsayers Scientists", "color": "Violet", "ia": "PredictEinstein (intelligente)"},
}


def clear_terminal():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def compute_team_stats(game: Game):
    stats = {}
    for u in game.alive_units():
        team = getattr(u, "team", "?")
        if team not in stats:
            stats[team] = {"units": 0, "total_hp": 0.0, "by_type": {}}
        stats[team]["units"] += 1
        stats[team]["total_hp"] += float(u.hp)
        tname = type(u).__name__
        stats[team]["by_type"][tname] = stats[team]["by_type"].get(tname, 0) + 1
    return stats


def render(game: Game):
    print(f"Temps simulé : {game.time:.1f}")
    stats = compute_team_stats(game)

    print("=== État des armées ===")
    for team, st in stats.items():
        info = TEAM_INFO.get(team, {})
        label = info.get("name", f"Équipe {team}")
        color = info.get("color", "?")
        ia_name = info.get("ia", "?")
        print(
            f"- {label} (team={team}, couleur={color}, IA={ia_name}) : "
            f"{st['units']} unités en vie, HP total ≈ {st['total_hp']:.1f}"
        )
        compo = ", ".join(f"{cnt}x {t}" for t, cnt in st["by_type"].items())
        print(f"    Composition : {compo}")
    print()

    print("Unités en vie :")
    for u in game.alive_units():
        print(
            f"- {type(u).__name__} (team={u.team}), "
            f"HP={u.hp:.1f}, pos=({u.x:.2f},{u.y:.2f})"
        )
    print()

    print("Événements récents :")
    for log in game.logs[-7:]:
        print(" ", log)
    print()


def log_state_to_file(game: Game, step: int, filepath: str):
    def format_intent(u):
        intent = getattr(u, "intent", None)
        if intent is None:
            return "none"
        kind = intent[0]
        if kind == "move_to":
            _, tx, ty = intent
            return f"move_to({tx:.2f},{ty:.2f})"
        if kind == "attack":
            _, target = intent
            if target is None or not hasattr(target, "hp"):
                return "attack(?)"
            return f"attack({target.__class__.__name__})"
        return str(kind)

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(
            f"===== STEP {step} | temps simulé = {game.time:.2f} s =====\n"
        )
        for u in game.alive_units():
            line = (
                f"- team={getattr(u, 'team', '?')}, "
                f"type={type(u).__name__}, "
                f"HP={u.hp:.1f}, "
                f"pos=({u.x:.2f},{u.y:.2f}), "
                f"intent={format_intent(u)}\n"
            )
            f.write(line)
        f.write("\n")


def write_battle_summary(game: Game, filepath: str):
    summary = game.get_battle_summary()

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("===== RÉSUMÉ DE LA BATAILLE =====\n\n")
        f.write(f"Durée simulée : {summary['duration']:.2f} s\n")
        f.write(f"Gagnant : {summary['winner']}\n\n")

        f.write("---- Composition initiale ----\n")
        for team, stats in summary["initial_counts"].items():
            f.write(f"Équipe {team} : {stats['units']} unités\n")
            for tname, cnt in stats["by_type"].items():
                f.write(f"   - {cnt}x {tname}\n")
        f.write("\n")

        f.write("---- Survivants ----\n")
        for team, stats in summary["survivors"].items():
            f.write(f"Équipe {team} : {stats['units']} unités en vie\n")
            for tname, cnt in stats["by_type"].items():
                f.write(f"   - {cnt}x {tname}\n")
        f.write("\n")

        f.write("---- Pertes ----\n")
        for team, stats in summary["losses"].items():
            f.write(f"Équipe {team} : {stats['units']} unités perdues\n")
            for tname, cnt in stats["by_type"].items():
                f.write(f"   - {cnt}x {tname}\n")
        f.write("\n")

        f.write("---- Dégâts infligés / subis ----\n")
        for team, dmg in summary["team_damage"].items():
            recv = summary["team_damage_received"].get(team, 0.0)
            kills = summary["kills"].get(team, 0)
            f.write(
                f"Équipe {team} : "
                f"dégâts infligés = {dmg:.1f}, "
                f"dégâts subis = {recv:.1f}, "
                f"kills = {kills}\n"
            )


def main():
    # 1) Construire le scénario (on pourra changer ici pour un autre scénario)
    game = scenario_simple_vs_braindead()

    dt = 0.2
    max_time = 200.0
    step_index = 0

    state_log_file = "battle_state.txt"
    with open(state_log_file, "w", encoding="utf-8") as f:
        f.write("LOG D'ÉTAT PAR STEP (temps continu)\n\n")

    # 2) Boucle de simulation
    while not game.is_finished() and game.time < max_time:
        step_index += 1
        game.step(dt=dt)
        log_state_to_file(game, step_index, state_log_file)

        clear_terminal()
        print(f"===== Step {step_index} | temps simulé = {game.time:.1f} s =====")
        render(game)
        time.sleep(0.1)

    print("===== Fin de la bataille =====")
    render(game)

    winner = game.get_winner()
    if winner is None:
        print("Match nul.")
    else:
        info = TEAM_INFO.get(winner, {})
        label = info.get("name", f"Équipe {winner}")
        ia_name = info.get("ia", "?")
        print(f"Victoire de {label} (team {winner}, IA={ia_name}) !")

    # 3) Résumé de bataille
    write_battle_summary(game, "battle_summary.txt")
    print("\nRésumé de bataille écrit dans battle_summary.txt")


if __name__ == "__main__":
    main()
