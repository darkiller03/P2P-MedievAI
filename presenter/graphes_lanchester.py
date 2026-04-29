#!/usr/bin/env python3
"""
graphes_lanchester.py - Analyse approfondie des lois de Lanchester

Ce module fournit des outils d'analyse avancés pour vérifier si les batailles
du jeu respectent les lois mathématiques de Lanchester.

Utilisable via CLI ou directement comme script.
"""

import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

# Imports corrigés pour l'architecture MVP
from model.scenarios import (
    scenario_simple_vs_braindead,
    scenario_small_terminal,
    scenario_lanchester,
)


def calculer_puissance_unite(u):
    """Calcule la puissance de combat d'une unité."""
    attack = 0

    # Attaque de mêlée
    if hasattr(u, 'baseMelee'):
        attack = u.baseMelee

    # Attaque perçante
    if hasattr(u, 'basePierceAttack'):
        attack = max(attack, u.basePierceAttack)

    # Attaque standard (fallback)
    if attack == 0:
        attack = getattr(u, 'attaque', 10)

    # Facteur de cadence (tirs par seconde)
    reload_time = getattr(u, 'reloadTime', 2.0)
    cadence = 1.0 / reload_time

    # Facteur de portée (unités à distance plus efficaces)
    unit_range = getattr(u, 'range', 1.0)
    range_bonus = 1.0 + (unit_range * 0.05)

    # HP comme facteur de survie
    hp = getattr(u, 'hp', 100)
    hp_factor = hp / 100.0

    return attack * cadence * range_bonus * hp_factor


def simuler_lanchester(game, max_time=200, dt=0.1):
    """
    Simule l'évolution des effectifs selon les équations différentielles de Lanchester.

    Retourne : (temps, histoire_a, histoire_b, ka, kb)
    """
    # Extraire les données de départ
    unites_a = [u for u in game.units if u.team == "A"]
    unites_b = [u for u in game.units if u.team == "B"]

    a0 = len(unites_a)
    b0 = len(unites_b)

    # Calcul de la puissance de combat
    puissance_totale_a = sum(calculer_puissance_unite(u) for u in unites_a)
    puissance_totale_b = sum(calculer_puissance_unite(u) for u in unites_b)

    ka = puissance_totale_a / (a0 * 100) if a0 > 0 else 0.01
    kb = puissance_totale_b / (b0 * 100) if b0 > 0 else 0.01

    # Simulation
    history_a = [a0]
    history_b = [b0]
    temps = [0]

    curr_a, curr_b = float(a0), float(b0)
    while curr_a > 0.5 and curr_b > 0.5:
        # Équations de Lanchester : da/dt = -kb*b, db/dt = -ka*a
        nouv_a = curr_a - (kb * curr_b * dt)
        nouv_b = curr_b - (ka * curr_a * dt)

        curr_a = max(0, nouv_a)
        curr_b = max(0, nouv_b)

        history_a.append(curr_a)
        history_b.append(curr_b)
        temps.append(temps[-1] + dt)

        if temps[-1] > max_time:
            break

    return temps, history_a, history_b, ka, kb


def simuler_bataille_reelle(scenario_func, max_time=200, dt=0.1):
    """
    Lance une vraie simulation de bataille.

    Retourne : (temps, histoire_a, histoire_b, winner)
    """
    game = scenario_func()

    temps_reel = [0]
    histoire_a = [len(game.alive_units_of_team("A"))]
    histoire_b = [len(game.alive_units_of_team("B"))]

    while not game.is_finished() and game.time < max_time:
        game.step(dt=dt)
        temps_reel.append(game.time)
        histoire_a.append(len(game.alive_units_of_team("A")))
        histoire_b.append(len(game.alive_units_of_team("B")))

    winner = game.get_winner()
    return temps_reel, histoire_a, histoire_b, winner


def plot_comparaison_lanchester(scenario_func, scenario_name="Bataille", save_plot=True):
    """
    Compare la prédiction Lanchester avec une vraie simulation.
    Génère un graphique complet avec 4 sous-graphiques.

    Retourne : (pred_winner, real_winner, erreur_moyenne)
    """
    print(f"\n{'='*60}")
    print(f"  ANALYSE : {scenario_name}")
    print(f"{'='*60}\n")

    # 1. Prédiction Lanchester
    print("[THEORIE] Calcul de la prediction Lanchester...")
    game_lanchester = scenario_func()
    temps_l, hist_a_l, hist_b_l, ka, kb = simuler_lanchester(game_lanchester)

    a0 = hist_a_l[0]
    b0 = hist_b_l[0]

    print(f"   Equipe A : {int(a0)} unites, k = {ka:.4f}")
    print(f"   Equipe B : {int(b0)} unites, k = {kb:.4f}")

    # Prédiction du vainqueur Lanchester
    if hist_a_l[-1] > hist_b_l[-1]:
        pred_winner = "A"
        pred_survivors = hist_a_l[-1]
    elif hist_b_l[-1] > hist_a_l[-1]:
        pred_winner = "B"
        pred_survivors = hist_b_l[-1]
    else:
        pred_winner = "Nul"
        pred_survivors = 0

    print(f"   [PRED] Prediction : Victoire {pred_winner}")
    print(f"   [TIME] Duree estimee : {temps_l[-1]:.1f}s")
    print(f"   [SURV] Survivants estimes : {pred_survivors:.1f}\n")

    # 2. Simulation réelle
    print("[SIMUL] Lancement de la simulation reelle...")
    temps_r, hist_a_r, hist_b_r, real_winner = simuler_bataille_reelle(scenario_func)

    print(f"   [WIN] Resultat reel : Victoire {real_winner if real_winner else 'Nul'}")
    print(f"   [TIME] Duree reelle : {temps_r[-1]:.1f}s")

    real_survivors_a = hist_a_r[-1]
    real_survivors_b = hist_b_r[-1]
    print(f"   [SURV] Survivants reels : A={real_survivors_a}, B={real_survivors_b}\n")

    # 3. Comparaison
    print("[COMP] Comparaison :")
    pred_match = "[OK] CORRECT" if pred_winner == real_winner else "[KO] INCORRECT"
    print(f"   Prediction du vainqueur : {pred_match}")

    time_diff = abs(temps_l[-1] - temps_r[-1])
    print(f"   Écart de durée : {time_diff:.1f}s ({time_diff/temps_r[-1]*100:.1f}%)")

    # 4. Graphique comparatif
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(f'Analyse Lanchester vs Réel : {scenario_name}',
                 fontsize=16, fontweight='bold')

    # Graphique 1 : Prédiction Lanchester
    ax1 = axes[0, 0]
    ax1.plot(temps_l, hist_a_l, 'b-', label=f'A (Lanchester)', linewidth=2.5)
    ax1.plot(temps_l, hist_b_l, 'r-', label=f'B (Lanchester)', linewidth=2.5)
    ax1.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    ax1.set_title('[THEORIE] Prediction Theorique (Lanchester)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Temps (s)')
    ax1.set_ylabel('Nombre d\'unités')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.text(0.02, 0.98, f'Vainqueur prédit : {pred_winner}',
             transform=ax1.transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Graphique 2 : Simulation réelle
    ax2 = axes[0, 1]
    ax2.plot(temps_r, hist_a_r, 'b-', label=f'A (Réel)', linewidth=2.5, marker='o', markersize=2)
    ax2.plot(temps_r, hist_b_r, 'r-', label=f'B (Réel)', linewidth=2.5, marker='o', markersize=2)
    ax2.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    ax2.set_title('[SIMUL] Simulation Reelle', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Temps (s)')
    ax2.set_ylabel('Nombre d\'unités')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.text(0.02, 0.98, f'Vainqueur réel : {real_winner if real_winner else "Nul"}',
             transform=ax2.transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

    # Graphique 3 : Superposition
    ax3 = axes[1, 0]
    ax3.plot(temps_l, hist_a_l, 'b--', label='A (Lanchester)', linewidth=2, alpha=0.7)
    ax3.plot(temps_l, hist_b_l, 'r--', label='B (Lanchester)', linewidth=2, alpha=0.7)
    ax3.plot(temps_r, hist_a_r, 'b-', label='A (Réel)', linewidth=2)
    ax3.plot(temps_r, hist_b_r, 'r-', label='B (Réel)', linewidth=2)
    ax3.set_title('[COMP] Comparaison Directe', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Temps (s)')
    ax3.set_ylabel('Nombre d\'unités')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Graphique 4 : Erreur absolue
    ax4 = axes[1, 1]

    # Interpolation pour comparer sur les mêmes points temporels
    temps_commun = np.linspace(0, min(temps_l[-1], temps_r[-1]), 100)

    hist_a_l_interp = np.interp(temps_commun, temps_l, hist_a_l)
    hist_b_l_interp = np.interp(temps_commun, temps_l, hist_b_l)
    hist_a_r_interp = np.interp(temps_commun, temps_r, hist_a_r)
    hist_b_r_interp = np.interp(temps_commun, temps_r, hist_b_r)

    erreur_a = np.abs(hist_a_l_interp - hist_a_r_interp)
    erreur_b = np.abs(hist_b_l_interp - hist_b_r_interp)

    ax4.plot(temps_commun, erreur_a, 'b-', label='Erreur A', linewidth=2)
    ax4.plot(temps_commun, erreur_b, 'r-', label='Erreur B', linewidth=2)
    ax4.fill_between(temps_commun, erreur_a, alpha=0.3, color='blue')
    ax4.fill_between(temps_commun, erreur_b, alpha=0.3, color='red')
    ax4.set_title('[ERROR] Erreur Absolue (|Lanchester - Reel|)', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Temps (s)')
    ax4.set_ylabel('Écart (unités)')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    erreur_moy_a = np.mean(erreur_a)
    erreur_moy_b = np.mean(erreur_b)
    erreur_moy = (erreur_moy_a + erreur_moy_b) / 2
    ax4.text(0.02, 0.98, f'Erreur moy A : {erreur_moy_a:.2f}\nErreur moy B : {erreur_moy_b:.2f}',
             transform=ax4.transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

    plt.tight_layout()

    if save_plot:
        filename = f"lanchester_vs_reel_{scenario_name.replace(' ', '_')}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"[SAVE] Graphique sauvegarde : {filename}\n")

    plt.show()

    return pred_winner, real_winner, erreur_moy


def plot_loi_carree(unit_types, max_n=20, save_plot=True, num_runs=5):
    """
    Vérifie la loi carrée de Lanchester sur plusieurs types d'unités.

    Combat N vs 2N : B (2N unités) gagne toujours.
    Survivants de B = sqrt((2N)² - N²) = N*sqrt(3) ≈ 1.73*N

    Args:
        unit_types: liste de types d'unités (ex: ["knight", "crossbowman"])
        max_n: valeur maximale de N à tester
        save_plot: si True, sauvegarde le graphique
        num_runs: nombre de simulations par valeur de N (pour moyenner)

    Retourne : dict avec les résultats par type d'unité
    """
    # Import ici pour utiliser MajorDaft (poursuit les ennemis = combat réel)
    from presenter.ai import MajorDaft
    
    if isinstance(unit_types, str):
        unit_types = [unit_types]

    print(f"\n{'='*60}")
    print(f"  VÉRIFICATION LOI CARRÉE DE LANCHESTER")
    print(f"  Types d'unité : {', '.join([u.upper() for u in unit_types])}")
    print(f"  Runs par valeur : {num_runs}")
    print(f"{'='*60}\n")

    all_results = {}

    for unit_type in unit_types:
        print(f"\n--- Test {unit_type.upper()} ---")

        resultats_n = []
        resultats_survivants_b = []
        resultats_theoriques = []

        for n in range(2, max_n + 1, 2):
            print(f"Test N = {n}...", end=" ")

            survivants_runs = []
            
            for run in range(num_runs):
                # Créer le scénario N vs 2N avec MajorDaft (poursuit l'ennemi le plus proche)
                controllers = {
                    "A": MajorDaft("A"),
                    "B": MajorDaft("B"),
                }
                game = scenario_lanchester(unit_type, n, controllers=controllers)

                # Simulation réelle
                while not game.is_finished() and game.time < 300:
                    game.step(dt=0.2)

                # Compter les survivants de B (l'équipe qui gagne)
                survivants_b = len(game.alive_units_of_team("B"))
                survivants_runs.append(survivants_b)
            
            # Moyenne des runs
            survivants_b_moy = sum(survivants_runs) / len(survivants_runs)

            # Théorie : Survivants de B = sqrt((2N)² - N²) = N*sqrt(3)
            survivants_theoriques = n * np.sqrt(3)

            resultats_n.append(n)
            resultats_survivants_b.append(survivants_b_moy)
            resultats_theoriques.append(survivants_theoriques)

            print(f"Survivants B = {survivants_b_moy:.1f} (théorie : {survivants_theoriques:.1f})")

        all_results[unit_type] = {
            'N': resultats_n,
            'survivants_reels': resultats_survivants_b,
            'survivants_theoriques': resultats_theoriques
        }

    # Graphique
    n_types = len(unit_types)
    fig, axes = plt.subplots(n_types, 2, figsize=(14, 5*n_types))
    if n_types == 1:
        axes = axes.reshape(1, -1)

    fig.suptitle('Vérification Loi Carrée de Lanchester', fontsize=16, fontweight='bold')

    for idx, unit_type in enumerate(unit_types):
        data = all_results[unit_type]

        # Graphique 1 : Comparaison survivants réels vs théoriques
        ax1 = axes[idx, 0]
        ax1.plot(data['N'], data['survivants_reels'], 'o-', label='Survivants réels (B)',
                 linewidth=2, markersize=8, color='red')
        ax1.plot(data['N'], data['survivants_theoriques'], 's--', label='Survivants théoriques (N×√3)',
                 linewidth=2, markersize=6, color='blue', alpha=0.7)
        ax1.set_xlabel('N (taille armée A)', fontsize=12)
        ax1.set_ylabel('Survivants de B après victoire', fontsize=12)
        ax1.set_title(f'Loi Carrée - {unit_type.capitalize()}', fontsize=13, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)

        # Graphique 2 : Erreur
        ax2 = axes[idx, 1]
        erreur = np.array(data['survivants_reels']) - np.array(data['survivants_theoriques'])
        ax2.bar(data['N'], erreur, color='purple', alpha=0.6)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax2.set_xlabel('N (taille armée A)', fontsize=12)
        ax2.set_ylabel('Écart (Réel - Théorique)', fontsize=12)
        ax2.set_title(f'Écart - {unit_type.capitalize()}', fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')

        # Ajouter statistiques
        erreur_moy = np.mean(np.abs(erreur))
        ax2.text(0.98, 0.98, f'Erreur moyenne : {erreur_moy:.2f}',
                 transform=ax2.transAxes, verticalalignment='top', horizontalalignment='right',
                 bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

    plt.tight_layout()

    if save_plot:
        filename = f"loi_carree_{'_'.join(unit_types)}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n[SAVE] Graphique sauvegarde : {filename}\n")

    plt.show()

    return all_results


def menu_principal():
    """Menu interactif pour choisir l'analyse."""
    print("\n" + "="*60)
    print("  [LANCHESTER] ANALYSEUR DE LANCHESTER - MedievAIl")
    print("="*60)
    print("\nChoisissez une analyse :")
    print("  1. Comparer Lanchester vs Réel (Scénario Standard)")
    print("  2. Comparer Lanchester vs Réel (Scénario Terminal)")
    print("  3. Vérifier la Loi Carrée (Knight)")
    print("  4. Vérifier la Loi Carrée (Pikeman)")
    print("  5. Vérifier la Loi Carrée (Crossbowman)")
    print("  6. Vérifier la Loi Carrée (Tous les types)")
    print("  7. Toutes les analyses")
    print("  0. Quitter")

    choix = input("\nVotre choix : ").strip()

    if choix == "1":
        plot_comparaison_lanchester(scenario_simple_vs_braindead, "Scénario Standard")
    elif choix == "2":
        plot_comparaison_lanchester(scenario_small_terminal, "Scénario Terminal")
    elif choix == "3":
        plot_loi_carree(["knight"], max_n=20)
    elif choix == "4":
        plot_loi_carree(["pikeman"], max_n=20)
    elif choix == "5":
        plot_loi_carree(["crossbowman"], max_n=20)
    elif choix == "6":
        plot_loi_carree(["knight", "pikeman", "crossbowman"], max_n=20)
    elif choix == "7":
        print("\n[RUN] Execution de toutes les analyses...\n")
        plot_comparaison_lanchester(scenario_simple_vs_braindead, "Scénario Standard")
        plot_comparaison_lanchester(scenario_small_terminal, "Scénario Terminal")
        plot_loi_carree(["knight", "pikeman", "crossbowman"], max_n=20)
        print("\n[OK] Toutes les analyses terminees !")
    elif choix == "0":
        print("\nAu revoir !")
        return
    else:
        print("\n❌ Choix invalide.")
        return

    # Proposer de continuer
    continuer = input("\n▶️  Faire une autre analyse ? (o/n) : ").strip().lower()
    if continuer == 'o':
        menu_principal()


if __name__ == "__main__":
    menu_principal()
