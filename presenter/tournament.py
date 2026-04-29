import time
from collections import defaultdict

# --- IMPORTS ---

from model.scenarios import (
    scenario_simple_vs_braindead,
    scenario_small_terminal,
    scenario_bataille_colline,
    scenario_deux_camps_eleves,
    scenario_siege_chateau,
)
from .ai import CaptainBraindead, MajorDaft, AssasinJack, PredictEinstein
from .smartAI import GeneralStrategus

# --- CONFIGURATION ---
AVAILABLE_GENERALS = {
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
    "Siege_Chateau": scenario_siege_chateau,
}

# --- MOTEUR HEADLESS (Match Rapide) ---
def run_headless_match(scenario_func, ai_class_A, ai_class_B, max_ticks=2000):
    game = scenario_func()
    # On écrase les contrôleurs par défaut
    game.controllers["A"] = ai_class_A("A")
    game.controllers["B"] = ai_class_B("B")
    
    ticks = 0
    # Boucle rapide sans affichage
    while not game.is_finished() and ticks < max_ticks:
        game.step(dt=0.2) 
        ticks += 1
        
    winner = game.get_winner()
    return "Draw" if winner is None else winner

# --- CLASSE TOURNOI ---
class Tournament:
    def __init__(self, generals_names, scenario_names, rounds=10):
        self.generals = generals_names
        self.scenarios = scenario_names
        self.rounds = rounds
       
        self.results = {} 

    def run(self):
        print(f"[TOURNEY] Lancement du tournoi : {len(self.generals)} Generaux, {len(self.scenarios)} Scenarios.")
        
        start_time = time.time()

        for sc_name in self.scenarios:
            print(f"\n--- [SCENARIO] {sc_name} ---")
            sc_func = AVAILABLE_SCENARIOS[sc_name]
            self.results[sc_name] = {}

            for name_1 in self.generals:
                self.results[sc_name][name_1] = {}
                
                for name_2 in self.generals:
                    ai_1 = AVAILABLE_GENERALS[name_1]
                    ai_2 = AVAILABLE_GENERALS[name_2]
                    
                    stats = {"wins": 0, "losses": 0, "draws": 0}
                    
                    # Barre de progression simple
                    print(f"  > {name_1} vs {name_2} ", end="", flush=True)
                    
                    for i in range(self.rounds):
                        # Alternance des positions (Fair-play)
                        if i % 2 == 0:
                            # Match Aller : 
                            res = run_headless_match(sc_func, ai_1, ai_2)
                            if res == "A": stats["wins"] += 1
                            elif res == "B": stats["losses"] += 1
                            else: stats["draws"] += 1
                        else:
                            # Match Retour : 
                            res = run_headless_match(sc_func, ai_2, ai_1)
                            if res == "A": stats["losses"] += 1 
                            elif res == "B": stats["wins"] += 1
                            else: stats["draws"] += 1
                        
                        # Un petit point tous les 5 matchs pour montrer que ça bosse
                        if i % 5 == 0: print(".", end="", flush=True)

                    self.results[sc_name][name_1][name_2] = stats
                    print(f" ({stats['wins']}V)")
                    
        duration = time.time() - start_time
        print(f"\n✅ Tournoi terminé en {duration:.1f}s !")
        self.generate_advanced_report()

    def generate_advanced_report(self):
        """ Génère le rapport HTML complet avec les 4 matrices demandées """
        
        # --- CALCUL DES STATS AGREGÉES ---
        
        # 1. Stats Globales par Général (Pour le tableau A)
        # global_stats[Gen] = {wins, total_games}
        global_stats = defaultdict(lambda: {"wins": 0, "total": 0})

        # 2. Stats Globales Gen vs Gen (Pour le tableau B)
        # matrix_global[Gen1][Gen2] = {wins, total}
        matrix_global = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "total": 0}))

        # 3. Stats Gen vs Scenario (Pour le tableau D)
        # matrix_scen[Gen][Scenario] = {wins, total}
        matrix_scen = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "total": 0}))

        # Compilation des données brutes
        for sc, matrix in self.results.items():
            for p1 in self.generals:
                for p2 in self.generals:
                    s = matrix[p1][p2]
                    w = s['wins']
                    t = s['wins'] + s['losses'] + s['draws']

                    # A. Global Score
                    global_stats[p1]['wins'] += w
                    global_stats[p1]['total'] += t

                    # B. Gen vs Gen (tous scénarios confondus)
                    matrix_global[p1][p2]['wins'] += w
                    matrix_global[p1][p2]['total'] += t

                    # D. Gen vs Scenario (tous opposants confondus)
                    matrix_scen[p1][sc]['wins'] += w
                    matrix_scen[p1][sc]['total'] += t

        # --- GÉNÉRATION HTML ---
        html = """
        <html><head><style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background: #f4f4f9; }
            h1, h2 { color: #333; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 30px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
            th, td { border: 1px solid #ddd; padding: 10px; text-align: center; }
            th { background-color: #007bff; color: white; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            .win-high { background-color: #d4edda; color: #155724; font-weight: bold; } /* Vert */
            .win-mid { background-color: #fff3cd; color: #856404; } /* Jaune */
            .win-low { background-color: #f8d7da; color: #721c24; } /* Rouge */
            .self { background-color: #e2e3e5; color: #666; font-style: italic; }
        </style></head><body>
        <h1>📊 Rapport de Tournoi - Age of Python</h1>
        """

        # --- FONCTION UTILITAIRE POUR LES CELLULES ---
        def get_cell_html(wins, total, is_self=False):
            if total == 0: return "<td>-</td>"
            pct = (wins / total) * 100
            css = "win-mid"
            if is_self: css = "self"
            elif pct >= 60: css = "win-high"
            elif pct <= 40: css = "win-low"
            return f"<td class='{css}'>{pct:.1f}%<br><small>({wins}/{total})</small></td>"

        # --- A. CLASSEMENT GÉNÉRAL (General Score) ---
        html += "<h2>A. Classement Général (Taux de victoire global)</h2>"
        html += "<table><tr><th>Rang</th><th>Général</th><th>Victoires</th><th>Matchs joués</th><th>% Victoire</th></tr>"
        
        # Tri par pourcentage de victoire
        sorted_gens = sorted(self.generals, key=lambda g: global_stats[g]['wins'], reverse=True)
        
        for rank, gen in enumerate(sorted_gens, 1):
            st = global_stats[gen]
            pct = (st['wins'] / st['total']) * 100 if st['total'] > 0 else 0
            html += f"<tr><td>#{rank}</td><td><strong>{gen}</strong></td><td>{st['wins']}</td><td>{st['total']}</td><td>{pct:.1f}%</td></tr>"
        html += "</table>"

        # --- B. MATRICE GLOBAL (Gen vs Gen) ---
        html += "<h2>B. Matrice Globale (Gen vs Gen - Tous scénarios)</h2>"
        html += "<table><tr><th>VS</th>" + "".join(f"<th>{g}</th>" for g in self.generals) + "</tr>"
        for p1 in self.generals:
            html += f"<tr><td><strong>{p1}</strong></td>"
            for p2 in self.generals:
                st = matrix_global[p1][p2]
                html += get_cell_html(st['wins'], st['total'], p1==p2)
            html += "</tr>"
        html += "</table>"

        # --- D. GEN vs SCENARIO (Performance) ---
        html += "<h2>D. Performance par Scénario</h2>"
        html += "<table><tr><th>Général</th>" + "".join(f"<th>{s}</th>" for s in self.scenarios) + "</tr>"
        for gen in self.generals:
            html += f"<tr><td><strong>{gen}</strong></td>"
            for sc in self.scenarios:
                st = matrix_scen[gen][sc]
                html += get_cell_html(st['wins'], st['total'])
            html += "</tr>"
        html += "</table>"

        # --- C. PAR SCÉNARIO (Détail) ---
        html += "<h2>C. Détail par Scénario (Gen vs Gen)</h2>"
        for sc in self.scenarios:
            html += f"<h3>📍 {sc}</h3>"
            html += "<table><tr><th>VS</th>" + "".join(f"<th>{g}</th>" for g in self.generals) + "</tr>"
            for p1 in self.generals:
                html += f"<tr><td><strong>{p1}</strong></td>"
                for p2 in self.generals:
                    st = self.results[sc][p1][p2]
                    total = st['wins'] + st['losses'] + st['draws']
                    html += get_cell_html(st['wins'], total, p1==p2)
                html += "</tr>"
            html += "</table>"

        html += "</body></html>"
        
        filename = "tournament_report.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n📄 Rapport généré : {filename}")

if __name__ == "__main__":
    # --- CONFIGURATION DU LANCEMENT ---
    # Liste des participants
    ai_participants = ["Braindead", "Daft", "GeneralStrategus", "AssasinJack"] 
   
    
    scenarios = ["Scenario_Standard","Scenario_Dur"]
    
    # 20 rounds = 10 allers + 10 retours pour chaque paire
    t = Tournament(ai_participants, scenarios, rounds=2)
    t.run()


