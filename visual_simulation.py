import pygame
import sys

# --- IMPORTS ---
from model.scenarios import scenario_simple_vs_braindead
from view.views import GUI

# --- TEAM INFO ---
TEAM_INFO = {
    "A": {"name": "Kingdom of the North", "color": "Bleu", "ia": "MajorDaft (agressive)"},
    "B": {"name": "Empire of the South", "color": "Rouge", "ia": "Captain BRAINDEAD (statique)"},
    "C": {"name": "Smart Alliance", "color": "Vert", "ia": "GeneralStrategus (intelligente)"},
    "D": {"name": "The Ripper Coven", "color": "Jaune", "ia": "AssasinJack (intelligente)"},
    "E": {"name": "Soothsayers Scientists", "color": "Violet", "ia": "PredictEinstein (intelligente)"},
}

def main():
    print("Initialisation de la bataille...")
    game = scenario_simple_vs_braindead()

    pygame.init()
    
    START_W = 1024
    START_H = 768
    
    screen = pygame.display.set_mode((START_W, START_H), pygame.RESIZABLE)
    
    pygame.display.set_caption("Simulation : Age of Python")
    clock = pygame.time.Clock()

    view = GUI(game, START_W, START_H)
    
    auto_play = False
    game_over_processed = False 

    print("\n--- COMMANDES ---")
    print("[P]               : Lecture / Pause")
    print("[ESPACE]          : Pas à pas")
    print("[Molette]         : Zoomer / Dézoomer (centré sur souris)")
    print("[Clic/Clic Droit] : Maintenir pour déplacer la caméra")
    print("[M]               : Afficher/Cacher la minimap")
    print("[Flèches]         : Déplacer la caméra au clavier")
    print("[F11/F12]         : Sauvegarde/Chargement rapide")
    print("-----------------\n")

    running = True
    while running:
        # --- BOUCLE D'ÉVÉNEMENTS ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            view.handle_events(event)
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    if not game.is_finished():
                        auto_play = not auto_play
                        state = "LECTURE" if auto_play else "PAUSE"
                        print(f"État : {state}")
                
                if event.key == pygame.K_SPACE:
                    if not game.is_finished():
                        game.step(dt=0.1)
                        print(f"Tour joué. Temps: {game.time:.1f}")

                if event.key == pygame.K_F9:
                    print("Basculement vers la vue Terminal...")
                    pygame.quit()
                    from view.terminal_view import TerminalView
                    view = TerminalView(game)
                    view.start()
                    sys.exit()

        # --- LOGIQUE DE JEU (MODEL) ---
        if not game.is_finished():
            if auto_play:
                game.step(dt=0.02)
        
        else:
            if not game_over_processed:
                print("\n" + "="*30)
                print("   LA BATAILLE EST TERMINÉE !")
                print("="*30)
                
                winner = game.get_winner()
                if winner is None:
                    print("🏁 RÉSULTAT : MATCH NUL")
                else:
                    info = TEAM_INFO.get(winner, {})
                    print(f"🏆 VAINQUEUR : {info.get('name', winner)}")
                
                print("="*30 + "\n")
                auto_play = False
                game_over_processed = True

        # --- AFFICHAGE (VIEW) ---
        
        view.handle_input() 
        
        view.draw(screen)
        
        if game.is_finished():
            winner = game.get_winner()
            font = pygame.font.SysFont("Arial", 40, bold=True)
            
            lines = []
            if winner is None:
                lines.append(("MATCH NUL", (255, 255, 255)))
            else:
                info = TEAM_INFO.get(winner, {})
                lines.append((f"VICTOIRE : {info.get('name', winner)}", (255, 215, 0)))
                lines.append((f"Général : {info.get('ia', '?')}", (200, 200, 200)))

            center_x = view.screen_w // 2 
            start_y = 100 
            
            for i, (txt, color) in enumerate(lines):
                surf = font.render(txt, True, color)
                rect = surf.get_rect(center=(center_x, start_y + i * 50))
                
                bg = pygame.Surface((rect.width + 20, rect.height + 10))
                bg.set_alpha(180)
                bg.fill((0, 0, 0))
                screen.blit(bg, bg.get_rect(center=rect.center))
                
                screen.blit(surf, rect)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()