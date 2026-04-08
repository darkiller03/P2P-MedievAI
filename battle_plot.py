import matplotlib.pyplot as plt
from Engine import SimpleEngine
from Generals import DaftGeneral
from Scenario_lanchester import lanchester_scenario

def run_simulation(unit_type, N):
    engine = SimpleEngine(60, 60)
    lanchester_scenario(engine, unit_type, N)
    generals = {1: DaftGeneral(1), 2: DaftGeneral(2)}
    dt = 0.2
    max_ticks = 300.0
    while engine.tick < max_ticks:
        engine.step(dt, generals)
        if not engine.get_units_for_player(1) or not engine.get_units_for_player(2):
            break
    return len(engine.get_units_for_player(2))

def generate_lanchester_plot(max_n=50):
    n_values = range(5, max_n + 1, 5)
    results = {"knight": [], "Crossbowman": []}
    print("Démarrage des simulations Lanchester...")
    for n in n_values:
        print(f"Test N={n}...", end="\r")
        results["knight"].append(run_simulation("knight", n))
        results["Crossbowman"].append(run_simulation("Crossbowman", n))

    plt.figure(figsize=(10, 6))
    plt.plot(n_values, results["knight"], 'r-o', label='Mêlée (Loi Linéaire)')
    plt.plot(n_values, results["Crossbowman"], 'b-s', label='Distance (Loi Quadratique)')
    plt.plot(n_values, n_values, 'r--', alpha=0.3, label='Théorie Linéaire (y=N)')
    plt.plot(n_values, [1.73 * n for n in n_values], 'b--', alpha=0.3, label='Théorie Quadratique (y=1.73N)')
    plt.xlabel('N (P1: N vs P2: 2N)')
    plt.ylabel('Survivants P2')
    plt.title('Validation Lanchester')
    plt.legend()
    plt.grid(True)
    plt.savefig('lanchester_validation.png')
    print("\nGraphique généré : lanchester_validation.png")

if __name__ == "__main__":
    generate_lanchester_plot()
