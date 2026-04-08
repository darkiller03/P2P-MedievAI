import pygame
from typing import Dict, Tuple
from Engine import SimpleEngine
from Generals import General
from Units import Unit
from Map import TILE_SIZE, MAP_W, MAP_H
from GameState import GameStateManager
from DebugInfo import DebugInfoGenerator
import os
import math
SCREEN_W, SCREEN_H = 960, 640
FPS = 60
camera_speed = 10.0

def clamp(v, a, b): return max(a, min(b, v))
class PygameRenderer:
    def __init__(self, engine: SimpleEngine, generals: Dict[int, General]):
        if pygame is None:
            raise RuntimeError("Pygame not installed.")
        pygame.init()
        self.engine = engine
        self.generals = generals
        
        # Set fullscreen mode
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        global SCREEN_W, SCREEN_H
        SCREEN_W, SCREEN_H = self.screen.get_size()
        
        pygame.display.set_caption("MedievAIl prototype")
        self.clock = pygame.time.Clock()
        self.cam_x = max(0, engine.w//2 - (SCREEN_W // TILE_SIZE)//2)
        self.cam_y = max(0, engine.h//2 - (SCREEN_H // TILE_SIZE)//2)
        self.speed_multiplier = 1.0
        self.paused = False
        self.show_minimap = True
        
        # Zoom
        self.zoom = 1.0
        self.min_zoom = 0.5
        self.max_zoom = 3.0
        
        # UI toggles (F1-F4)
        self.show_army_info = True
        self.show_health_bars = True
        self.show_ai_debug = False
        
        # Game state management
        self.state_manager = GameStateManager()
        self.debug_generator = DebugInfoGenerator()
        
        # Pause menu
        self.show_pause_menu = False
        
        # Game end state
        self.game_over = False
        self.winner = None
        self.game_over_tick = None
        
        # Load textures
        self.load_textures()

    def tile_size(self) -> int:
        return max(4, int(TILE_SIZE * self.zoom))

    def load_textures(self):
        """Load all terrain and unit textures"""
        assets_path = os.path.join(os.path.dirname(__file__), 'assets')
        
        # Load single grass and stretch over the whole map (no tiling)
        self.grass_bg = None
        self.grass_bg_size = (MAP_W * TILE_SIZE, MAP_H * TILE_SIZE)
        try:
            grass1 = pygame.image.load(os.path.join(assets_path, 'terrain', 'background.png')).convert()
            self.grass_bg = pygame.transform.smoothscale(grass1, self.grass_bg_size)
        except Exception as e:
            print(f"Warning: Could not load terrain texture: {e}")
            self.grass_bg = None
        
        # Load unit textures: {(unit_type, player, direction): surface}
        self.unit_textures = {}
        unit_types = ['Pikeman', 'Crossbowman', 'Knight', 'Monk']  # Removed Long_Swordman - no sprites
        colors = {1: 'red', 2: 'blue'}
        directions = ['up', 'down', 'left', 'right']
        
        for unit_type in unit_types:
            for player, color in colors.items():
                for direction in directions:
                    try:
                        path = os.path.join(assets_path, 'units', unit_type, color, f'{direction}.png')
                        img = pygame.image.load(path)
                        img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                        self.unit_textures[(unit_type, player, direction)] = img
                    except Exception as e:
                        pass  # Silently skip missing textures
                    pass

    def get_unit_direction(self, unit: Unit) -> str:
        """Determine which direction the unit is facing based on target or last movement"""
        if not hasattr(unit, 'last_x'):
            unit.last_x = unit.x
            unit.last_y = unit.y
        
        # Calculate direction based on target
        target = None
        if unit.target_id and unit.target_id in self.engine.units_by_id:
            target = self.engine.units_by_id[unit.target_id]
        
        if target:
            dx = target.x - unit.x
            dy = target.y - unit.y
        else:
            dx = unit.x - unit.last_x
            dy = unit.y - unit.last_y
        
        # Store current position for next frame
        unit.last_x = unit.x
        unit.last_y = unit.y
        
        # Determine direction based on angle
        if abs(dx) > abs(dy):
            return 'right' if dx > 0 else 'left'
        else:
            return 'down' if dy > 0 else 'up'

    def world_to_screen(self, wx, wy) -> Tuple[int,int]:
        t = self.tile_size()
        sx = int((wx - self.cam_x) * t)
        sy = int((wy - self.cam_y) * t)
        return sx, sy

    def draw(self):
        # Check for game over condition
        self.check_game_over()
        
        t = self.tile_size()

        # Always fill screen first to avoid black borders when zoomed out
        self.screen.fill((34, 139, 34))

        # Draw single stretched background (no tiling), large enough to cover view
        if self.grass_bg:
            bg_w = int(self.grass_bg_size[0] * self.zoom)
            bg_h = int(self.grass_bg_size[1] * self.zoom)

            # Ensure background at least covers screen at current zoom
            bg_w = max(bg_w, SCREEN_W)
            bg_h = max(bg_h, SCREEN_H)

            scaled_bg = pygame.transform.smoothscale(self.grass_bg, (bg_w, bg_h))
            offset_x = -int(self.cam_x * t)
            offset_y = -int(self.cam_y * t)
            self.screen.blit(scaled_bg, (offset_x, offset_y))
        
        # Draw units
        for u in self.engine.units:
            t = self.tile_size()
            sx, sy = self.world_to_screen(u.x, u.y)
            
            # Get unit type (normalize name)
            unit_type = u.unit_type
            if unit_type.lower().startswith('pik'):
                unit_type = 'Pikeman'
            elif unit_type.lower().startswith('cross'):
                unit_type = 'Crossbowman'
            elif unit_type.lower().startswith('knight'):
                unit_type = 'Knight'
            elif unit_type.lower().startswith('monk'):
                unit_type = 'Monk'
            
            # Get direction
            direction = self.get_unit_direction(u)
            
            # Try to use texture, fallback to circle
            texture_key = (unit_type, u.player, direction)
            if texture_key in self.unit_textures:
                sprite = pygame.transform.scale(self.unit_textures[texture_key], (t, t))
                self.screen.blit(sprite, (sx, sy))
            else:
                col = u.color
                r = int(t * 0.4)
                self.screen.blit(pygame.Surface((t, t), pygame.SRCALPHA), (sx, sy))
                pygame.draw.circle(self.screen, col, (sx + t//2, sy + t//2), r)
            
            # Draw HP bar
            if self.show_health_bars:
                hp_frac = clamp(u.hp / u.max_hp, 0.0, 1.0)
                bar_w = int(t * hp_frac)
                pygame.draw.rect(self.screen, (0,0,0), (sx, sy-6, t, 4))
                pygame.draw.rect(self.screen, (0,255,0), (sx, sy-6, bar_w, 4))
        
        # Draw HUD
        self.draw_hud()
        
        # Draw game over screen if game is over
        if self.game_over:
            self.draw_game_over_screen()
        # Draw pause menu if active
        elif self.show_pause_menu:
            self.draw_pause_menu()
        
        pygame.display.flip()
    
    def draw_hud(self):
        """Draw the heads-up display"""
        font = pygame.font.SysFont(None, 20)
        font_small = pygame.font.SysFont(None, 16)
        
        # Main info
        status = "PAUSED" if self.paused else "RUNNING"
        txt = f"Tick: {self.engine.tick:.2f}  Units: {len(self.engine.units)}  Speed x{self.speed_multiplier:.1f}  [{status}]"
        surf = font.render(txt, True, (255,255,255))
        self.screen.blit(surf, (8,8))
        
        # Army info (F1)
        if self.show_army_info:
            y_offset = 30
            p1_units = len(self.engine.get_units_for_player(1))
            p2_units = len(self.engine.get_units_for_player(2))
            
            p1_txt = font_small.render(f"Player 1 (Red): {p1_units} units", True, (255,100,100))
            p2_txt = font_small.render(f"Player 2 (Blue): {p2_units} units", True, (100,150,255))
            self.screen.blit(p1_txt, (8, y_offset))
            self.screen.blit(p2_txt, (8, y_offset + 18))
        
        # Controls help
        help_y = SCREEN_H - 80
        controls = [
            "P:Pause | TAB:Debug | F9:Switch View | F11:Save | F12:Load | ESC:Menu",
            "ZQSD/Arrows:Move | +/-:Speed | F1:Army | F2:Map | F3:HP | Space:Fast"
        ]
        for i, ctrl in enumerate(controls):
            ctrl_surf = font_small.render(ctrl, True, (200,200,200))
            self.screen.blit(ctrl_surf, (8, help_y + i*18))
        
        # Minimap (F2)
        if self.show_minimap:
            mm_w, mm_h = 200,200
            mm_surf = pygame.Surface((mm_w, mm_h))
            mm_surf.fill((20,20,20))
            scale_x = mm_w / self.engine.w
            scale_y = mm_h / self.engine.h
            
            # Draw camera viewport on minimap
            t = self.tile_size()
            cam_w = (SCREEN_W / t) * scale_x
            cam_h = (SCREEN_H / t) * scale_y
            cam_x_mm = self.cam_x * scale_x
            cam_y_mm = self.cam_y * scale_y
            pygame.draw.rect(mm_surf, (100,100,100), (cam_x_mm, cam_y_mm, cam_w, cam_h), 2)
            
            # Draw units
            for u in self.engine.units:
                ux = int(u.x*scale_x)
                uy = int(u.y*scale_y)
                c = (255,50,50) if u.player==1 else (50,50,255)
                mm_surf.fill(c, (ux, uy, 2,2))
            
            self.screen.blit(mm_surf, (SCREEN_W - mm_w - 8, 8))
    
    def check_game_over(self):
        """Check if game is over (one team eliminated)"""
        if self.game_over:
            return
        
        p1_alive = len(self.engine.get_units_for_player(1))
        p2_alive = len(self.engine.get_units_for_player(2))
        
        if p1_alive == 0 and p2_alive > 0:
            self.game_over = True
            self.winner = 2
            self.game_over_tick = self.engine.tick
        elif p2_alive == 0 and p1_alive > 0:
            self.game_over = True
            self.winner = 1
            self.game_over_tick = self.engine.tick
    
    def draw_game_over_screen(self):
        """Draw game over overlay with winner"""
        overlay = pygame.Surface((SCREEN_W, SCREEN_H))
        overlay.set_alpha(200)
        overlay.fill((0,0,0))
        self.screen.blit(overlay, (0,0))
        
        font_title = pygame.font.SysFont(None, 80)
        font_text = pygame.font.SysFont(None, 40)
        
        title = font_title.render("GAME OVER", True, (255,255,0))
        title_rect = title.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 100))
        self.screen.blit(title, title_rect)
        
        if self.winner == 1:
            winner_text = font_text.render("PLAYER 1 (RED) WINS!", True, (255,100,100))
        else:
            winner_text = font_text.render("PLAYER 2 (BLUE) WINS!", True, (100,150,255))
        
        winner_rect = winner_text.get_rect(center=(SCREEN_W//2, SCREEN_H//2))
        self.screen.blit(winner_text, winner_rect)
        
        info_text = font_text.render("Press ESC to continue", True, (200,200,200))
        info_rect = info_text.get_rect(center=(SCREEN_W//2, SCREEN_H//2 + 100))
        self.screen.blit(info_text, info_rect)
    
    def draw_pause_menu(self):
        """Draw the ESC pause menu overlay"""
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_W, SCREEN_H))
        overlay.set_alpha(180)
        overlay.fill((0,0,0))
        self.screen.blit(overlay, (0,0))
        
        # Menu box
        menu_w, menu_h = 400, 300
        menu_x = (SCREEN_W - menu_w) // 2
        menu_y = (SCREEN_H - menu_h) // 2
        
        pygame.draw.rect(self.screen, (40,40,40), (menu_x, menu_y, menu_w, menu_h))
        pygame.draw.rect(self.screen, (100,100,100), (menu_x, menu_y, menu_w, menu_h), 3)
        
        # Title
        font_title = pygame.font.SysFont(None, 36)
        font_item = pygame.font.SysFont(None, 24)
        
        title = font_title.render("PAUSED", True, (255,255,255))
        title_rect = title.get_rect(center=(SCREEN_W//2, menu_y + 40))
        self.screen.blit(title, title_rect)
        
        # Menu items
        items = [
            "ESC or P - Resume",
            "F11 - Quick Save",
            "F12 - Quick Load",
            "F9 - Switch View",
            "TAB - Debug Info",
            "Q - Quit"
        ]
        
        for i, item in enumerate(items):
            text = font_item.render(item, True, (200,200,200))
            text_rect = text.get_rect(center=(SCREEN_W//2, menu_y + 100 + i*30))
            self.screen.blit(text, text_rect)

    def handle_input(self):
        """Handle continuous keyboard input for camera movement"""
        keys = pygame.key.get_pressed()
        dt = self.clock.get_time()/1000.0
        
        # Fast scroll with Shift
        speed_mult = 3.0 if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else 1.0
        move_speed = camera_speed * dt * speed_mult / max(0.5, self.zoom)
        
        # ZQSD + Arrow keys for movement
        if keys[pygame.K_LEFT] or keys[pygame.K_a] or keys[pygame.K_q]: 
            self.cam_x -= move_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: 
            self.cam_x += move_speed
        if keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_z]: 
            self.cam_y -= move_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: 
            self.cam_y += move_speed
        
        # Clamp camera to map bounds (in world units)
        t = self.tile_size()
        view_w = SCREEN_W / t
        view_h = SCREEN_H / t
        self.cam_x = clamp(self.cam_x, 0, max(0, self.engine.w - view_w))
        self.cam_y = clamp(self.cam_y, 0, max(0, self.engine.h - view_h))
        
        # Space for fast-forward
        if keys[pygame.K_SPACE]:
            self.speed_multiplier = 4.0
        elif not (keys[pygame.K_PLUS] or keys[pygame.K_EQUALS] or keys[pygame.K_MINUS]):
            # Reset speed if not manually adjusting
            if self.speed_multiplier == 4.0:
                self.speed_multiplier = 1.0

    def run(self):
        """Main game loop for PyGame renderer"""
        running = True
        switch_to_terminal = False
        
        while running:
            dt_real = self.clock.tick(FPS)/1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
                elif event.type == pygame.KEYDOWN:
                    # ESC - Toggle pause menu or exit if game over
                    if event.key == pygame.K_ESCAPE:
                        if self.game_over:
                            running = False
                        else:
                            self.show_pause_menu = not self.show_pause_menu
                            self.paused = self.show_pause_menu
                    
                    # Q - Quit
                    elif event.key == pygame.K_q and self.show_pause_menu:
                        running = False
                    
                    # P - Pause/Resume
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused
                        if not self.paused:
                            self.show_pause_menu = False
                    
                    # F9 - Switch to terminal view
                    elif event.key == pygame.K_F9:
                        switch_to_terminal = True
                        running = False
                    
                    # F11 - Quick Save
                    elif event.key == pygame.K_F11:
                        if self.state_manager.quick_save(self.engine, self.generals):
                            print("✓ Game saved!")
                    
                    # F12 - Quick Load
                    elif event.key == pygame.K_F12:
                        state = self.state_manager.quick_load()
                        if state:
                            self.state_manager.restore_engine(state, self.engine)
                            self.generals = self.state_manager.restore_generals(state)
                            print("✓ Game loaded!")
                        else:
                            print("✗ No save file found!")
                    
                    # TAB - Generate debug info
                    elif event.key == pygame.K_TAB:
                        filepath = self.debug_generator.generate_html(self.engine, self.generals)
                        print(f"✓ Debug report generated: {filepath}")
                    
                    # F1 - Toggle army info
                    elif event.key == pygame.K_F1:
                        self.show_army_info = not self.show_army_info
                    
                    # F2 - Toggle minimap
                    elif event.key == pygame.K_F2:
                        self.show_minimap = not self.show_minimap
                    
                    # F3 - Toggle health bars
                    elif event.key == pygame.K_F3:
                        self.show_health_bars = not self.show_health_bars
                    
                    # F4 - Toggle AI debug overlays
                    elif event.key == pygame.K_F4:
                        self.show_ai_debug = not self.show_ai_debug
                    
                    # M - Toggle minimap (legacy)
                    elif event.key == pygame.K_m:
                        self.show_minimap = not self.show_minimap
                    
                    # +/= - Increase speed
                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        self.speed_multiplier = min(self.speed_multiplier * 2.0, 16.0)
                    
                    # - - Decrease speed
                    elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
                        self.speed_multiplier = max(self.speed_multiplier / 2.0, 0.125)

                    # Zoom in
                    elif event.key == pygame.K_PAGEUP:
                        self.zoom = min(self.max_zoom, self.zoom + 0.1)
                    # Zoom out
                    elif event.key == pygame.K_PAGEDOWN:
                        self.zoom = max(self.min_zoom, self.zoom - 0.1)
                    # Center on fight (bounding box of alive units)
                    elif event.key == pygame.K_f:
                        alive = [u for u in self.engine.units if u.alive]
                        if alive:
                            min_x = min(u.x for u in alive)
                            max_x = max(u.x for u in alive)
                            min_y = min(u.y for u in alive)
                            max_y = max(u.y for u in alive)
                            cx = (min_x + max_x) / 2
                            cy = (min_y + max_y) / 2
                            tsize = self.tile_size()
                            view_w = SCREEN_W / tsize
                            view_h = SCREEN_H / tsize
                            self.cam_x = clamp(cx - view_w/2, 0, max(0, self.engine.w - view_w))
                            self.cam_y = clamp(cy - view_h/2, 0, max(0, self.engine.h - view_h))
                
                # Mouse click on minimap
                elif event.type == pygame.MOUSEBUTTONDOWN and self.show_minimap:
                    mouse_x, mouse_y = event.pos
                    mm_x = SCREEN_W - 208
                    mm_y = 8
                    mm_w, mm_h = 200, 200
                    
                    if mm_x <= mouse_x <= mm_x + mm_w and mm_y <= mouse_y <= mm_y + mm_h:
                        # Click on minimap - move camera
                        rel_x = (mouse_x - mm_x) / mm_w
                        rel_y = (mouse_y - mm_y) / mm_h
                        t = self.tile_size()
                        view_w = SCREEN_W / t
                        view_h = SCREEN_H / t
                        self.cam_x = rel_x * self.engine.w - view_w / 2
                        self.cam_y = rel_y * self.engine.h - view_h / 2
                        self.cam_x = clamp(self.cam_x, 0, max(0, self.engine.w - view_w))
                        self.cam_y = clamp(self.cam_y, 0, max(0, self.engine.h - view_h))

                # Mouse wheel zoom
                elif event.type == pygame.MOUSEWHEEL:
                    if event.y > 0:
                        self.zoom = min(self.max_zoom, self.zoom + 0.1)
                    elif event.y < 0:
                        self.zoom = max(self.min_zoom, self.zoom - 0.1)
            
            # Handle continuous input
            self.handle_input()
            
            # Update simulation if not paused and game is not over
            if not self.paused and not self.game_over:
                sim_dt = dt_real * self.speed_multiplier
                sim_dt = min(sim_dt, 0.5)
                self.engine.step(sim_dt, self.generals)
            
            # Render
            self.screen.fill((0,0,0))
            self.draw()
        
        pygame.quit()

        return 'switch_terminal' if switch_to_terminal else None
