import curses
import time
import os
import webbrowser
from dataclasses import dataclass

@dataclass
class Camera:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    def move(self, dx, dy, limit_w, limit_h):
        self.x = max(0, min(limit_w - self.width, self.x + dx))
        self.y = max(0, min(limit_h - self.height, self.y + dy))
        
    def center_on(self, target_x, target_y, limit_w, limit_h):
        """ Place la caméra pour que (target_x, target_y) soit au centre """
        self.x = target_x - (self.width // 2)
        self.y = target_y - (self.height // 2)
        # On reste dans les limites
        self.x = max(0, min(limit_w - self.width, self.x))
        self.y = max(0, min(limit_h - self.height, self.y))

class TerminalView:
    UNIT_CHARS = {
        'Knight': 'K', 'Pikeman': 'P', 'Crossbowman': 'C',
        'Castle': '#', 'Wonder': 'W'
    }

    def __init__(self, game):
        self.game = game
        self.map = game.map
        self.stdscr = None
        
        self.camera = Camera(0, 0, 0, 0)
        self.paused = False
        self.message = ""
        self.tick_speed = 30
        
        # --- INTELLIGENCE CAMÉRA ---
        self.auto_follow = True  # Activé par défaut

        # Couleurs
        self.COLOR_A = 1
        self.COLOR_B = 2
        self.COLOR_UI = 3

    def start(self):
        """ Point d'entrée principal """
        curses.wrapper(self._main_loop)

    def _init_colors(self):
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(self.COLOR_A, curses.COLOR_CYAN, -1)
        curses.init_pair(self.COLOR_B, curses.COLOR_RED, -1)
        curses.init_pair(self.COLOR_UI, curses.COLOR_YELLOW, -1)
        curses.curs_set(0) 

    def _update_camera_auto(self):
        """ Calcule le barycentre des unités pour centrer la caméra """
        if not self.auto_follow: return

        units = self.game.alive_units()
        if not units: return

        # Moyenne des positions X et Y
        sum_x = sum(float(getattr(u, 'x', 0)) for u in units)
        sum_y = sum(float(getattr(u, 'y', 0)) for u in units)
        avg_x = int(sum_x / len(units))
        avg_y = int(sum_y / len(units))

        # Application
        self.camera.center_on(avg_x, avg_y, self.map.cols, self.map.rows)

    def _main_loop(self, stdscr):
        self.stdscr = stdscr
        self.stdscr.nodelay(True)
        self._init_colors()

        last_time = time.time()

        while not self.game.is_finished():
            # 1. Gestion Entrées
            self._handle_input()

            # 2. Logique
            if not self.paused:
                current_time = time.time()
                if current_time - last_time > (1 / self.tick_speed):
                    self.game.step(dt=0.1)
                    last_time = current_time

            # 3. Mise à jour Caméra Auto
            self._update_camera_auto()

            # 4. Affichage
            self._draw()
            time.sleep(0.01)

        self._draw_game_over()

    def _handle_input(self):
        try: key = self.stdscr.getch()
        except: return
        if key == -1: return

        # --- ZQSD : DÉSACTIVE LE MODE AUTO ---
        if key in [ord('z'), ord('Z')]: 
            self.auto_follow = False
            self.camera.move(0, -1, self.map.cols, self.map.rows)
        elif key in [ord('s'), ord('S')]: 
            self.auto_follow = False
            self.camera.move(0, 1, self.map.cols, self.map.rows)
        elif key in [ord('q'), ord('Q')]: 
            self.auto_follow = False
            self.camera.move(-1, 0, self.map.cols, self.map.rows)
        elif key in [ord('d'), ord('D')]: 
            self.auto_follow = False
            self.camera.move(1, 0, self.map.cols, self.map.rows)
        
        # --- 'A' ou 'C' : RÉACTIVE LE MODE AUTO ---
        elif key in [ord('a'), ord('A'), ord('c'), ord('C')]:
            self.auto_follow = True
            self.message = "CAMÉRA AUTO"

        # Pause
        elif key in [ord('p'), ord('P')]:
            self.paused = not self.paused
            self.message = "PAUSE" if self.paused else ""

        # Snapshot HTML
        elif key == 9: # TAB
            self.paused = True
            self.generate_html_snapshot()
            self.message = "SNAPSHOT HTML !"

        # Vitesse
        elif key == ord('+'): self.tick_speed += 5
        elif key == ord('-'): self.tick_speed = max(1, self.tick_speed - 5)

        # Quitter
        elif key == 27: exit()

    def _draw(self):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        
        ui_height = 4
        map_h = h - ui_height - 2
        map_w = w - 2
        
        self.camera.width = min(self.map.cols, map_w)
        self.camera.height = min(self.map.rows, map_h)

        self._draw_border(0, 0, map_w + 2, map_h + 2)

        for unit in self.game.alive_units():
            ux = int(unit.x) - self.camera.x
            uy = int(unit.y) - self.camera.y

            if 0 <= ux < self.camera.width and 0 <= uy < self.camera.height:
                char = self.UNIT_CHARS.get(type(unit).__name__, '?')
                team = getattr(unit, 'team', '?')
                color = curses.color_pair(self.COLOR_A) if team == 'A' else curses.color_pair(self.COLOR_B)
                try: self.stdscr.addch(uy + 1, ux + 1, char, color | curses.A_BOLD)
                except: pass

        # UI Stats
        mode_cam = "AUTO" if self.auto_follow else "MANUEL"
        stats = f"Time: {self.game.time:.1f}s | Units: {len(self.game.alive_units())} | Cam: {mode_cam}"
        self.stdscr.addstr(h - 3, 2, stats, curses.color_pair(self.COLOR_UI))
        self.stdscr.addstr(h - 2, 2, "Controls: A(Auto) ZQSD(Manuel) P(Pause) TAB(Snapshot) ESC(Quit)", curses.color_pair(self.COLOR_UI))
        
        if self.message:
            self.stdscr.addstr(h - 4, 2, f"*** {self.message} ***", curses.color_pair(self.COLOR_UI) | curses.A_BLINK)

        self.stdscr.refresh()

    def _draw_border(self, y, x, w, h):
        try:
            self.stdscr.hline(y, x, '-', w)
            self.stdscr.hline(y + h - 1, x, '-', w)
            self.stdscr.vline(y, x, '|', h)
            self.stdscr.vline(y, x + w - 1, '|', h)
            self.stdscr.addch(y, x, '+')
            self.stdscr.addch(y, x + w - 1, '+')
            self.stdscr.addch(y + h - 1, x, '+')
            self.stdscr.addch(y + h - 1, x + w - 1, '+')
        except: pass

    def _draw_game_over(self):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        msg = f"GAME OVER - Winner: {self.game.get_winner()}"
        self.stdscr.addstr(h//2, w//2 - len(msg)//2, msg, curses.A_BOLD)
        self.stdscr.addstr(h//2 + 1, w//2 - 10, "Press any key to quit")
        self.stdscr.nodelay(False)
        self.stdscr.getch()

    def generate_html_snapshot(self):
        """
        Génère un snapshot HTML complet avec:
        - Informations des unités (HP, position, intent)
        - État des IA/contrôleurs
        - Sections repliables par équipe
        """
        filename = "snapshot_terminal.html"
        
        # Helper pour formater l'intent
        def format_intent(u):
            intent = getattr(u, 'intent', None)
            if intent is None:
                return "<em>aucun</em>"
            kind = intent[0]
            if kind == "move_to":
                _, tx, ty = intent
                return f"Déplacement vers ({tx:.1f}, {ty:.1f})"
            if kind == "attack":
                _, target = intent
                if target is None or not hasattr(target, 'hp'):
                    return "Attaque (cible morte)"
                return f"Attaque {type(target).__name__} (HP:{target.hp:.0f})"
            return str(kind)
        
        # Grouper les unités par équipe
        units_by_team = {'A': [], 'B': []}
        for u in self.game.alive_units():
            team = getattr(u, 'team', '?')
            if team in units_by_team:
                units_by_team[team].append(u)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Snapshot - Temps {self.game.time:.1f}s</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
        h1 {{ color: #00d9ff; border-bottom: 2px solid #00d9ff; }}
        h2 {{ cursor: pointer; padding: 10px; margin: 0; }}
        h2:hover {{ background: #333; }}
        .team-a {{ background: #0a3d62; }}
        .team-b {{ background: #78281F; }}
        .section {{ margin-bottom: 20px; border-radius: 8px; overflow: hidden; }}
        .content {{ padding: 10px; background: #16213e; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #0f3460; }}
        .hp-bar {{ width: 100px; height: 10px; background: #333; border-radius: 5px; overflow: hidden; }}
        .hp-fill {{ height: 100%; background: linear-gradient(90deg, #00ff88, #00cc66); }}
        .intent {{ font-style: italic; color: #aaa; }}
        .ai-state {{ background: #2d3436; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .collapsed .content {{ display: none; }}
    </style>
    <script>
        function toggle(id) {{
            document.getElementById(id).classList.toggle('collapsed');
        }}
    </script>
</head>
<body>
    <h1>⚔️ Snapshot de Bataille - Temps: {self.game.time:.1f}s</h1>
    <p>Unités en vie: {len(self.game.alive_units())} | 
       Équipe A: {len(units_by_team['A'])} | 
       Équipe B: {len(units_by_team['B'])}</p>
    
    <div class="ai-state">
        <h3>🤖 État des Généraux (IA)</h3>
        <table>
            <tr><th>Équipe</th><th>Type IA</th><th>Intervalle décision</th></tr>
"""
        
        # Afficher l'état des contrôleurs
        for team, controller in self.game.controllers.items():
            ai_type = type(controller).__name__
            interval = getattr(controller, 'decision_interval', '?')
            color = "#00d9ff" if team == "A" else "#ff6b6b"
            html += f'<tr><td style="color:{color}">Équipe {team}</td><td>{ai_type}</td><td>{interval}s</td></tr>'
        
        html += """
        </table>
    </div>
"""
        
        # Sections par équipe
        for team, units in units_by_team.items():
            team_class = "team-a" if team == "A" else "team-b"
            team_name = "Équipe A (Bleu)" if team == "A" else "Équipe B (Rouge)"
            
            html += f"""
    <div id="section-{team}" class="section">
        <h2 class="{team_class}" onclick="toggle('section-{team}')">
            📋 {team_name} - {len(units)} unités (cliquer pour replier)
        </h2>
        <div class="content">
            <table>
                <tr>
                    <th>Type</th>
                    <th>HP</th>
                    <th>Position</th>
                    <th>Vitesse</th>
                    <th>Cooldown</th>
                    <th>Intent (Ordre actuel)</th>
                </tr>
"""
            for u in sorted(units, key=lambda x: type(x).__name__):
                hp = getattr(u, 'hp', 0)
                max_hp = 100  # Approximation
                hp_pct = min(100, (hp / max_hp) * 100)
                
                html += f"""
                <tr>
                    <td><strong>{type(u).__name__}</strong></td>
                    <td>
                        <div class="hp-bar">
                            <div class="hp-fill" style="width:{hp_pct}%"></div>
                        </div>
                        {hp:.0f}
                    </td>
                    <td>({u.x:.1f}, {u.y:.1f})</td>
                    <td>{getattr(u, 'speed', '?')}</td>
                    <td>{getattr(u, 'cooldown', 0):.1f}s</td>
                    <td class="intent">{format_intent(u)}</td>
                </tr>
"""
            
            html += """
            </table>
        </div>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        
        try:
            webbrowser.open(filename)
        except:
            pass