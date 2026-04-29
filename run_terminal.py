from view.terminal_view import TerminalView

from model.scenarios import scenario_lanchester

def main():
    # 1. Créer le jeu
    game = scenario_lanchester("knight",50)
    
    # 2. Créer la vue
    view = TerminalView(game)
    
    # 3. Lancer !
    view.start()

if __name__ == "__main__":
    main()