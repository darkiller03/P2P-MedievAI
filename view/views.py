import pygame
import math
import os
import pickle

# --- CONSTANTES DE BASE ---
TILE_WIDTH = 64
TILE_HEIGHT = 32
DEFAULT_SCREEN_W = 1024
DEFAULT_SCREEN_H = 768

# Configuration Minimap
MINIMAP_WIDTH = 300
MINIMAP_MARGIN = 20
MINIMAP_BORDER = 2

# Couleurs
COLOR_TEAM_A = (0, 80, 255)
COLOR_TEAM_B = (220, 20, 60)
COLOR_MINIMAP_BG = (30, 30, 30)
COLOR_VIEWPORT = (255, 255, 255)
COLOR_PANEL_BG = (10, 7, 4, 220)
COLOR_TEXT = (215, 190, 135)

# --- GESTION ANIMATION ---
class AnimationManager:
    def __init__(self):
        self.animations = {}
        self.default_assets = {}

    def load_spritesheet(self, unit_name, action, path, rows=8, cols=15, target_size=(100, 100)):
        if not os.path.exists(path):
            print(f"Warning: Sprite {path} not found.")
            return False

        try:
            sheet = pygame.image.load(path).convert_alpha()
            sheet_w, sheet_h = sheet.get_size()
            frame_w = sheet_w // cols
            frame_h = sheet_h // rows

            if unit_name not in self.animations:
                self.animations[unit_name] = {}
            if action not in self.animations[unit_name]:
                self.animations[unit_name][action] = {}

            for r in range(rows):
                frames = []
                for c in range(cols):
                    rect = pygame.Rect(c*frame_w, r*frame_h, frame_w, frame_h)
                    try:
                        sub = sheet.subsurface(rect)
                        scaled = pygame.transform.smoothscale(sub, target_size)
                        frames.append(scaled)
                    except ValueError:
                        pass
                self.animations[unit_name][action][r] = frames
            
            print(f"Loaded animation: {unit_name} / {action} ({rows} dirs, {cols} frames)")
            return True
        except Exception as e:
            print(f"Error loading sprite {path}: {e}")
            return False

    def load_static_sprite(self, unit_name, action, path, target_size=(100, 100)):
        """Charge une image unique comme une animation statique (1 frame, toutes directions)"""
        if not os.path.exists(path):
            print(f"Warning: Sprite {path} not found.")
            return False
            
        try:
            img = pygame.image.load(path).convert_alpha()
            scaled = pygame.transform.smoothscale(img, target_size)
            
            if unit_name not in self.animations: self.animations[unit_name] = {}
            if action not in self.animations[unit_name]: self.animations[unit_name][action] = {}
            
            frame_list = [scaled]
            for r in range(16):
                self.animations[unit_name][action][r] = frame_list
                
            print(f"Loaded static sprite: {unit_name} / {action}")
            return True
        except Exception as e:
            print(f"Error loading static sprite {path}: {e}")
            return False

    def get_frame(self, unit_name, action, direction, frame_idx):
        if unit_name not in self.animations:
            return None

        anim_set = self.animations[unit_name].get(action)
        if not anim_set:
            anim_set = self.animations[unit_name].get('idle')
        if not anim_set:
            anim_set = self.animations[unit_name].get('walk')

        if not anim_set:
            return None

        d = direction % 8
        if d not in anim_set:
            d = next(iter(anim_set.keys()), 0)

        frames = anim_set[d]
        if not frames:
            return None

        return frames[frame_idx % len(frames)]

class GUI:
    def __init__(self, game_instance, screen_width=DEFAULT_SCREEN_W, screen_height=DEFAULT_SCREEN_H):
        self.game = game_instance
        self.map = getattr(game_instance, 'map', None)
        
        self.screen_w = screen_width
        self.screen_h = screen_height
        
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        self.min_zoom = 0.1 # Allow zooming out much further
        self.max_zoom = 2.0
        
        # Fit entire map on screen at startup
        if self.map:
            rows = getattr(self.map, 'rows', 20)
            cols = getattr(self.map, 'cols', 20)
            iso_w = (cols + rows) * TILE_WIDTH / 2
            iso_h = (cols + rows) * TILE_HEIGHT / 2
            zoom_w = screen_width / iso_w if iso_w > 0 else 1.0
            zoom_h = screen_height / iso_h if iso_h > 0 else 1.0
            self.zoom = max(self.min_zoom, min(zoom_w, zoom_h) * 0.92)
            self.center_camera_on(rows // 2, cols // 2)
        else:
            self.center_camera_on(10, 10)
        
        # --- SOLUTION DRAG & DROP ---
        self.is_dragging = False
        
        # UI States
        self.show_minimap = False
        self.show_panel_a = True
        self.show_panel_b = True
        self.show_details = True
        self.show_ui_master = True
        self.last_toggle_time = 0
        
        # --- ANIMATION SYSTEM ---
        self.anim_mgr = AnimationManager()
        self.assets = {}
        self.unit_states = {}
        self._load_assets()

        pygame.font.init()
        _fp = pygame.font.match_font("agmena paneuropean book") or pygame.font.match_font("agmena")
        if _fp:
            self.font_ui = pygame.font.Font(_fp, 14)
            self.font_title = pygame.font.Font(_fp, 16)
        else:
            self.font_ui = pygame.font.SysFont("Georgia", 14)
            self.font_title = pygame.font.SysFont("Georgia", 16, bold=True)
        
        pygame.mouse.get_rel()

    def _load_assets(self):
        self.grass_tiles = {'normal': [], 'high': [], 'low': []}

        try:
            tileset = pygame.image.load("assets/background/grass.png").convert_alpha()
            ts_width, ts_height = tileset.get_size()

            slice_w = 128
            slice_h = 64

            cols = ts_width // slice_w
            rows = ts_height // slice_h

            for row in range(2):
                for col in range(cols):
                    rect = pygame.Rect(col * slice_w, row * slice_h, slice_w, slice_h)
                    tile = tileset.subsurface(rect).copy()
                    scaled = pygame.transform.smoothscale(tile, (TILE_WIDTH, TILE_HEIGHT))

                    self.grass_tiles['normal'].append(scaled)
                    self.grass_tiles['high'].append(scaled)
                    self.grass_tiles['low'].append(scaled)

            print(f"[TERRAIN] Tileset chargé: {len(self.grass_tiles)} tiles variées ({cols}×{rows})")

            # Fallback pour compatibilité
            if self.grass_tiles['normal']:
                self.assets['grass'] = self.grass_tiles['normal'][0]

        except Exception as e:
            print(f"[TERRAIN] Erreur chargement tileset: {e}")
            # Fallback: essayer l'ancienne méthode
            try:
                img = pygame.image.load("assets/grass.PNG").convert()
                img.set_colorkey(img.get_at((0,0)))
                scaled = pygame.transform.scale(img, (TILE_WIDTH, TILE_HEIGHT))
                self.assets['grass'] = scaled
                self.grass_tiles['normal'] = [scaled]
                self.grass_tiles['high'] = [scaled]
                self.grass_tiles['low'] = [scaled]
            except:
                s = pygame.Surface((TILE_WIDTH, TILE_HEIGHT))
                s.fill((34, 139, 34))
                self.assets['grass'] = s
                self.grass_tiles['normal'] = [s]
                self.grass_tiles['high'] = [s]
                self.grass_tiles['low'] = [s]

        # 2. Load Unit Animations
        # Structure: assets/units/[UnitName]/[action]/[UnitName]_[action].webp
        # Unit Names in folders: Knight, Pikeman, crossbowman
        # Types in code (lowercase): knight, pikeman, crossbowman
        
        units_to_load = [
            ("knight", "Knight"),
            ("pikeman", "Pikeman"),
            ("crossbowman", "crossbowman")
        ]
        
        actions = ["walk", "idle", "attack", "death", "decay"]
        
        for code_name, folder_name in units_to_load:
            for action in actions:
                # Construct path
                filename = f"{folder_name}_{action}.webp"
                path = os.path.join("assets", "units", folder_name, action, filename)
                
                # Load with 16 rows (directions) and 30 columns (frames)
                # Frame size: 6000/30 = 200w, 3200/16=200h. Ratio 1:1.
                # Scale to 160x160
                self.anim_mgr.load_spritesheet(code_name, action, path, rows=16, cols=30, target_size=(160, 160))
                
        # 3. Load Icons for UI (Static Fallbacks)
        # (Pass)

        # 3b. Load STATIC Units (Wonder) outside the loop
        # Wonder is big (5x5 tiles -> approx 320x320 px or more)
        # Original sprite is 82KB, size unknown, assume we want it big.
        wp = "assets/wonder.png"
        # Reduced from 256 to 192 to better fit visual expectations
        self.anim_mgr.load_static_sprite("wonder", "idle", wp, target_size=(192, 192))
        # Add fallback for 'walk' etc so it doesn't crash or disappear
        self.anim_mgr.load_static_sprite("wonder", "walk", wp, target_size=(192, 192))
        self.anim_mgr.load_static_sprite("wonder", "death", wp, target_size=(192, 192))

        # 4. Load GUI Custom Assets
        try:
            # Load Pointer
            p_img = pygame.image.load("assets/Pointer/attack48x48 (Copy).webp").convert_alpha()
            self.pointer_img = pygame.transform.scale(p_img, (32, 32)) # Resize if needed, or keep original
            
            # Load Minimap Panel
            pan_img = pygame.image.load("assets/minimapPan/map-panel.webp").convert_alpha()
            # Scaling panel to fit or surround the minimap area?
            # Minimap is MINIMAP_WIDTH wide. Let's see original size or just load it.
            self.minimap_panel_img = pan_img
        except Exception as e:
            print(f"Error loading GUI assets: {e}")
            self.pointer_img = None
            self.minimap_panel_img = None

        pygame.mouse.set_visible(True)

    def get_scaled_tile_size(self):
        # Force integer size to prevent rounding gaps (black lines) between tiles
        return math.ceil(TILE_WIDTH * self.zoom), math.ceil(TILE_HEIGHT * self.zoom)

    def cart_to_iso(self, row, col):
        w, h = self.get_scaled_tile_size()
        iso_x = (col - row) * (w / 2)
        iso_y = (row + col) * (h / 2)
        return iso_x, iso_y

    def iso_to_grid(self, x, y):
        w, h = self.get_scaled_tile_size()
        adj_x = x - self.camera_x
        adj_y = y - self.camera_y
        half_w = w / 2
        half_h = h / 2
        col = (adj_y / half_h + adj_x / half_w) / 2
        row = (adj_y / half_h - adj_x / half_w) / 2
        return int(row), int(col)

    def center_camera_on(self, row, col):
        target_x, target_y = self.cart_to_iso(row, col)
        self.camera_x = (self.screen_w // 2) - target_x
        self.camera_y = (self.screen_h // 2) - target_y

    # --- 1. GESTION DES CLICS (EVENTS) ---
    def handle_events(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.screen_w, self.screen_h = event.w, event.h

        elif event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            old_zoom = self.zoom
            world_x = (mouse_x - self.camera_x) / old_zoom
            world_y = (mouse_y - self.camera_y) / old_zoom

            if event.y > 0:
                self.zoom = min(self.max_zoom, self.zoom + 0.1)
            elif event.y < 0:
                self.zoom = max(self.min_zoom, self.zoom - 0.1)

            self.camera_x = mouse_x - world_x * self.zoom
            self.camera_y = mouse_y - world_y * self.zoom

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            if event.button in [1, 2, 3]:
                if event.button == 1 and self._is_click_on_minimap(mx, my):
                    pass
                else:
                    self.is_dragging = True
                    pygame.mouse.get_rel()

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button in [1, 2, 3]:
                self.is_dragging = False

    # --- 2. GESTION CONTINUE (BOUCLE) ---
    def handle_input(self):
        keys = pygame.key.get_pressed()
        
        s = 20 / self.zoom 
        if keys[pygame.K_LEFT]: self.camera_x += s
        if keys[pygame.K_RIGHT]: self.camera_x -= s
        if keys[pygame.K_UP]: self.camera_y += s
        if keys[pygame.K_DOWN]: self.camera_y -= s

        if self.is_dragging:
            dx, dy = pygame.mouse.get_rel()
            self.camera_x += dx
            self.camera_y += dy
        else:
            pygame.mouse.get_rel()

        current_time = pygame.time.get_ticks()
        if current_time - self.last_toggle_time > 200:
            if keys[pygame.K_F1]: self.show_panel_a = not self.show_panel_a; self.last_toggle_time = current_time
            if keys[pygame.K_F2]: self.show_panel_b = not self.show_panel_b; self.last_toggle_time = current_time
            if keys[pygame.K_F3]: self.show_details = not self.show_details; self.last_toggle_time = current_time
            if keys[pygame.K_F4]: self.show_ui_master = not self.show_ui_master; self.last_toggle_time = current_time
            if keys[pygame.K_m]: self.show_minimap = not self.show_minimap; self.last_toggle_time = current_time
            if keys[pygame.K_F11]: self._quick_save(); self.last_toggle_time = current_time
            if keys[pygame.K_F12]: self._quick_load(); self.last_toggle_time = current_time

        if self.show_minimap and self.show_ui_master and pygame.mouse.get_pressed()[0] and not self.is_dragging:
            self._handle_minimap_click()

        # --- CALIBRATION CONTROLS (TEMP) ---
        # T/G = Up/Down, F/H = Left/Right
        if not hasattr(self, 'panel_offset_x'): self.panel_offset_x = -21
        if not hasattr(self, 'panel_offset_y'): self.panel_offset_y = -6
        
        # Debounce slightly or just run fast? Run fast creates smoothness but prints a lot.
        # Let's use a small counter or just print every 10 frames if changed?
        # Simpler: just check pressed.
        changed = False
        if keys[pygame.K_t]: self.panel_offset_y -= 1; changed = True
        if keys[pygame.K_g]: self.panel_offset_y += 1; changed = True
        if keys[pygame.K_f]: self.panel_offset_x -= 1; changed = True
        if keys[pygame.K_h]: self.panel_offset_x += 1; changed = True
        
        if changed:
            print(f"CALIBRATION: X={self.panel_offset_x}, Y={self.panel_offset_y}")

    # --- HELPERS ANIMATION (NOUVEAU) ---
    def _update_unit_state(self, unit):
        """Met à jour l'état visuel (direction, action) basé sur la position et la vie."""
        uid = id(unit)
        now = pygame.time.get_ticks()
        is_dead = getattr(unit, 'hp', 0) <= 0
        
        if uid not in self.unit_states:
            # UNIFORM DEFAULT 15 (Left)
            # A (East) -> Inverted(0) = 15.
            # B (West) -> Standard(15) = 15.
            default_dir = 15
            
            self.unit_states[uid] = {
                'last_pos': (unit.x, unit.y),
                'last_time': now,
                'direction': default_dir,
                'action': 'idle',
                'frame_idx': 0,
                'accum_time': 0,
                'gone': False
            }
            if is_dead:
                 self.unit_states[uid]['action'] = 'death'
            
            return self.unit_states[uid]

        state = self.unit_states[uid]
        if state['gone']:
            return state

        dt = now - state['last_time']

        if is_dead and not getattr(unit, 'is_zombie', False):
            if state['action'] not in ['death', 'decay']:
                state['action'] = 'death'
                state['frame_idx'] = 0
                state['accum_time'] = 0

            state['accum_time'] += dt
            if state['accum_time'] > 100:
                state['accum_time'] = 0

                u_type = type(unit).__name__.lower()
                current_anim = self.anim_mgr.animations.get(u_type, {}).get(state['action'], {}).get(state['direction'], [])
                total_frames = len(current_anim)
                
                if state['frame_idx'] < total_frames - 1:
                    state['frame_idx'] += 1
                else:
                    if state['action'] == 'death':
                        state['action'] = 'decay'
                        state['frame_idx'] = 0
                    elif state['action'] == 'decay':
                         if not getattr(unit, 'is_zombie', False):
                             state['gone'] = True

        else:
            dx = unit.x - state['last_pos'][0]
            dy = unit.y - state['last_pos'][1]
            dist = math.hypot(dx, dy)
            is_moving = dist > 0.001

            current_cd = getattr(unit, 'cooldown', 0)
            last_cd = state.get('last_cooldown', 0)

            if current_cd > last_cd and not is_moving:
                 state['action'] = 'attack'
                 state['frame_idx'] = 0
                 state['accum_time'] = 0
            
            if is_moving:
                new_action = 'walk'
                angle = math.degrees(math.atan2(dy, dx))

                idx = int(abs(angle) / 180.0 * 15)
                idx = max(0, min(15, idx))
                idx = 15 - idx

                state['direction'] = idx

            elif state['action'] == 'attack':
                new_action = 'attack'

                intent = getattr(unit, 'intent', None)
                if intent and len(intent) >= 2 and intent[0] == 'attack':
                     target = intent[1]
                     if target and getattr(target, 'hp', 0) > 0:
                         dx_t = target.x - unit.x
                         dy_t = target.y - unit.y
                         angle_t = math.degrees(math.atan2(dy_t, dx_t))

                         idx_t = int(abs(angle_t) / 180.0 * 15)
                         idx_t = max(0, min(15, idx_t))
                         idx_t = 15 - idx_t

                         u_type_temp = type(unit).__name__.lower()
                         unit_team = getattr(unit, 'team', 'A')

                         if u_type_temp == 'crossbowman' and unit_team == 'B':
                             idx_t = (idx_t + 8) % 16

                         state['direction'] = idx_t

                u_type = type(unit).__name__.lower()
                current_anim = self.anim_mgr.animations.get(u_type, {}).get('attack', {}).get(state['direction'], [])

                if not current_anim or state['frame_idx'] >= len(current_anim) - 1:
                    new_action = 'idle'

            else:
                new_action = 'idle'

            if new_action != state['action']:
                if not (state['action'] == 'attack' and new_action == 'attack'):
                    state['action'] = new_action
                    state['frame_idx'] = 0
                    state['accum_time'] = 0
            else:
                state['accum_time'] += dt

                if state['accum_time'] > 100:
                    state['frame_idx'] += 1
                    state['accum_time'] = 0

            state['last_pos'] = (unit.x, unit.y)
            state['last_cooldown'] = current_cd
        
        return state

    def draw(self, screen):
        screen.fill((18, 32, 14))
        tw, th = self.get_scaled_tile_size()
        
        # Draw Map avec tileset varié selon élévation
        if self.map:
            rows = getattr(self.map, 'rows', 20); cols = getattr(self.map, 'cols', 20)

            for row in range(rows):
                for col in range(cols):
                    x, y = self.cart_to_iso(row, col); final_x = x + self.camera_x; final_y = y + self.camera_y
                    if -tw < final_x < self.screen_w and -th < final_y < self.screen_h:
                        # Récupérer l'élévation de cette tile
                        elev = self.map.get_elevation(row, col)

                        # Sélectionner la tile appropriée selon l'élévation
                        if elev > 0:
                            tile_category = 'high'
                        elif elev < 0:
                            tile_category = 'low'
                        else:
                            tile_category = 'normal'

                        # Ajouter de la variété : utiliser (row + col) comme seed pour sélection
                        tile_list = self.grass_tiles.get(tile_category, [])
                        if tile_list:
                            tile_index = (row * 7 + col * 13) % len(tile_list)  # Pseudo-random mais déterministe
                            tile_surf = tile_list[tile_index]
                        else:
                            # Fallback si pas de tileset
                            tile_surf = self.assets.get('grass')

                        # Redimensionner si nécessaire (pour le zoom)
                        if tile_surf:
                            if self.zoom != 1.0:
                                tile_surf = pygame.transform.scale(tile_surf, (int(tw), int(th)))
                            
                            # === EFFET VISUEL D'ÉLÉVATION ===
                            # 1. Décalage vertical pour effet 3D
                            elevation_tile_offset = 0
                            if elev > 0:
                                elevation_tile_offset = -6 * self.zoom  # Tuile élevée : monte vers le haut
                            elif elev < 0:
                                elevation_tile_offset = 4 * self.zoom   # Tuile basse : descend
                            
                            # 2. Teinte de couleur selon élévation (TRÈS SUBTILE)
                            if elev != 0:
                                # Créer une copie pour appliquer la teinte
                                tinted_tile = tile_surf.copy()
                                
                                if elev > 0:
                                    # Zone élevée : légère teinte dorée/chaude
                                    tint_overlay = pygame.Surface(tinted_tile.get_size(), pygame.SRCALPHA)
                                    tint_overlay.fill((40, 30, 10, 12))  # Très subtil doré
                                    tinted_tile.blit(tint_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                                else:
                                    # Zone basse : très légère teinte bleutée/froide
                                    tint_overlay = pygame.Surface(tinted_tile.get_size(), pygame.SRCALPHA)
                                    tint_overlay.fill((0, 0, 0, 15))  # Léger assombrissement
                                    tinted_tile.blit(tint_overlay, (0, 0))
                                
                                screen.blit(tinted_tile, (final_x, final_y + elevation_tile_offset))
                            else:
                                screen.blit(tile_surf, (final_x, final_y))

        # Draw ALL Units (Alive + Dead animating)
        # Note: game.alive_units() only gives living. We need self.game.units
        all_units = getattr(self.game, 'units', [])
        # Sort for depth (Painters algorithm)
        sorted_units = sorted(all_units, key=lambda u: u.x + u.y) 

        for unit in sorted_units:
            # Skip if hidden/gone
            state = self._update_unit_state(unit)
            if state.get('gone', False):
                continue
                
            u_x = getattr(unit, 'x', 0); u_y = getattr(unit, 'y', 0)
            x_iso, y_iso = self.cart_to_iso(u_x, u_y)
            screen_x = x_iso + self.camera_x; screen_y = y_iso + self.camera_y 
            
            if -150 < screen_x < self.screen_w and -150 < screen_y < self.screen_h:
                u_type = type(unit).__name__.lower()
                
                # Get Frame
                frame = self.anim_mgr.get_frame(u_type, state['action'], state['direction'], state['frame_idx'])
                
                if frame:
                    # Rendu spécifique pour les ZOMBIES RÉSEAU (Syndrome du mort-vivant)
                    if getattr(unit, 'is_zombie', False):
                        render_frame = frame.copy()
                        render_frame.fill((50, 255, 50, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    else:
                        render_frame = frame
                        
                    img_w = int(render_frame.get_width() * self.zoom)
                    img_h = int(render_frame.get_height() * self.zoom)
                    scaled_img = pygame.transform.scale(render_frame, (img_w, img_h))

                    # Calculer l'offset d'élévation pour effet de hauteur
                    elev = self.map.get_elevation(u_x, u_y) if self.map else 0.0
                    elevation_offset_y = 0
                    if elev > 0:
                        elevation_offset_y = -8 * self.zoom  # Élevé : 8 pixels vers le haut
                    elif elev < 0:
                        elevation_offset_y = 4 * self.zoom   # Bas : 4 pixels vers le bas
                    # Si elev == 0, offset = 0 (terrain plat)

                    draw_x = screen_x + (tw // 2) - (img_w // 2)
                    # FIX: Feet alignment calibrated by user to 0.50
                    draw_y = screen_y + (th // 2) - int(img_h * 0.50) + elevation_offset_y

                    is_alive = getattr(unit, 'hp', 0) > 0

                    if is_alive:
                        # Shadow & Team Circle only for living
                        team = getattr(unit, 'team', '?')
                        
                        # Scale shadow by unit radius (Default 0.5 for normal units)
                        u_radius = getattr(unit, 'radius', 0.5)
                        # Base size 30px for radius 0.5 -> linear scaling
                        # width = 30 * (radius / 0.5)
                        base_w = 30 * (u_radius / 0.5)
                        base_h = 15 * (u_radius / 0.5)
                        
                        ellipse_w = int(base_w * self.zoom)
                        ellipse_h = int(base_h * self.zoom)
                        
                        shadow_surf = pygame.Surface((ellipse_w, ellipse_h), pygame.SRCALPHA)
                        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 100), (0, 0, ellipse_w, ellipse_h))
                        shadow_x = screen_x + (tw // 2) - (ellipse_w // 2)
                        shadow_y = screen_y + (th // 2) - (ellipse_h // 4)
                        screen.blit(shadow_surf, (shadow_x, shadow_y))
                        
                        # Fix: Align colored circle with shadow (same Y offset)
                        pygame.draw.ellipse(screen, COLOR_TEAM_A if team == "A" else COLOR_TEAM_B, (screen_x + (tw//2) - ellipse_w//2, screen_y + (th//2) - ellipse_h//4, ellipse_w, ellipse_h), 1)

                    screen.blit(scaled_img, (draw_x, draw_y))
                    
                    if is_alive:
                        hp = getattr(unit, 'hp', 0)
                        max_hp = getattr(unit, 'max_hp', hp)
                        if hp > 0 and hp < max_hp:
                            bar_w = int(30 * self.zoom); bar_h = int(3 * self.zoom)
                            ratio = hp / max_hp
                            pygame.draw.rect(screen, (0,0,0), (draw_x + img_w//2 - bar_w//2, draw_y - 5, bar_w, bar_h))
                            color = (0, 255, 0)
                            if ratio < 0.3: color = (255, 0, 0)
                            pygame.draw.rect(screen, color, (draw_x + img_w//2 - bar_w//2, draw_y - 5, int(ratio * bar_w), bar_h))
                else:
                    if getattr(unit, 'hp', 0) > 0:
                         pygame.draw.circle(screen, (255, 255, 255), (int(screen_x), int(screen_y)), 10)

        self.draw_minimap(screen)
        self.draw_army_stats(screen)

        pass  # curseur systeme par defaut


    # ... Helper drawing methods ...
    # ... Helper drawing methods ...
    def draw_minimap(self, screen):
        if not self.show_minimap or not self.map or not self.show_ui_master: return
        max_rows = getattr(self.map, 'rows', 120)
        max_cols = getattr(self.map, 'cols', 120)
        base_iso_w = (max_cols + max_rows) * TILE_WIDTH / 2
        base_iso_h = (max_cols + max_rows) * TILE_HEIGHT / 2
        scale = MINIMAP_WIDTH / base_iso_w
        mini_height = base_iso_h * scale
        rect_x = self.screen_w - MINIMAP_WIDTH - MINIMAP_MARGIN
        rect_y = self.screen_h - mini_height - MINIMAP_MARGIN
        offset_x_world = max_rows * TILE_WIDTH / 2

        def to_mini(r, c):
            wx = (c - r) * (TILE_WIDTH // 2)
            wy = (r + c) * (TILE_HEIGHT // 2)
            mx = rect_x + (wx + offset_x_world) * scale
            my = rect_y + wy * scale
            return mx, my

        # Draw Panel Background (BEHIND the map)
        if self.minimap_panel_img:
             # Scale panel to be slightly larger than minimap to frame it
             margin_w = 50 # Reduced width
             margin_h = 20 # Reduced height
             
             panel_w = MINIMAP_WIDTH + margin_w
             panel_h = int(mini_height) + margin_h
             
             scaled_panel = pygame.transform.scale(self.minimap_panel_img, (panel_w, panel_h))
             
             # Align centers
             minimap_rect = pygame.Rect(rect_x, rect_y, MINIMAP_WIDTH, mini_height)
             panel_rect = scaled_panel.get_rect(center=minimap_rect.center)
             
             
             # MANUAL CORRECTION: Shift Left and Up (Calibration Mode)
             # Use self.panel_offset_x/y if they exist, else default
             off_x = getattr(self, 'panel_offset_x', -21) # Reduced left offset (Shifted right)
             off_y = getattr(self, 'panel_offset_y', -6)
             
             panel_rect.x += off_x
             panel_rect.y += off_y
             
             screen.blit(scaled_panel, panel_rect)
             
             # DEBUG: Draw red border around content and blue around panel to help alignment
             # pygame.draw.rect(screen, (255, 0, 0), minimap_rect, 1) # Content
             # pygame.draw.rect(screen, (0, 0, 255), panel_rect, 1)   # Panel Image

        # Draw Minimap Background Area (Strictly for the map content)
        # This draws ON TOP of the panel center, ensuring map is visible
        # REMOVED FOR CALIBRATION per User Request
        # pygame.draw.rect(screen, COLOR_MINIMAP_BG, (rect_x, rect_y, MINIMAP_WIDTH, mini_height))
        # Optional: Border around the map content itself?
        # pygame.draw.rect(screen, (255, 255, 255), (rect_x, rect_y, MINIMAP_WIDTH, mini_height), 1)

        p1 = to_mini(0, 0); p2 = to_mini(0, max_cols); p3 = to_mini(max_rows, max_cols); p4 = to_mini(max_rows, 0)
        pygame.draw.polygon(screen, (34, 139, 34), [p1, p2, p3, p4])
        pygame.draw.polygon(screen, (100, 200, 100), [p1, p2, p3, p4], 1)
        
        units = getattr(self.game, 'alive_units', lambda: [])()
        for unit in units:
            px, py = to_mini(getattr(unit, 'x', 0), getattr(unit, 'y', 0))
            color = COLOR_TEAM_A if getattr(unit, 'team', '?') == "A" else COLOR_TEAM_B
            pygame.draw.circle(screen, color, (int(px), int(py)), 3)

        view_w_world = self.screen_w / self.zoom
        view_h_world = self.screen_h / self.zoom
        cam_world_x = -self.camera_x / self.zoom
        cam_world_y = -self.camera_y / self.zoom
        mini_cam_x = rect_x + (cam_world_x + offset_x_world) * scale
        mini_cam_y = rect_y + cam_world_y * scale
        mini_cam_w = view_w_world * scale
        mini_cam_h = view_h_world * scale
        pygame.draw.rect(screen, COLOR_VIEWPORT, (mini_cam_x, mini_cam_y, mini_cam_w, mini_cam_h), 1)



    def draw_army_stats(self, screen):
        if not self.show_ui_master: return
        counts = {'A': {}, 'B': {}}; totals = {'A': 0, 'B': 0}
        units = getattr(self.game, 'alive_units', lambda: [])()
        for u in units:
            team = getattr(u, 'team', '?'); u_type = type(u).__name__
            if team not in counts: counts[team] = {}
            counts[team][u_type] = counts[team].get(u_type, 0) + 1; totals[team] += 1

        ai_name_a = type(self.game.controllers.get('A')).__name__ if 'A' in self.game.controllers else "?"
        ai_name_b = type(self.game.controllers.get('B')).__name__ if 'B' in self.game.controllers else "?"

        counts_a = counts.get('A', {})
        counts_b = counts.get('B', {})
        panel_h_a = 60 + (len(counts_a) * 20 + 8 if self.show_details else 0)
        if self.show_panel_a:
            self._draw_single_panel(screen, "Equipe A", ai_name_a, counts_a, totals.get('A', 0), 20, 20, COLOR_TEAM_A)
        b_y = (20 + panel_h_a + 8) if self.show_panel_a else 20
        if self.show_panel_b:
            self._draw_single_panel(screen, "Equipe B", ai_name_b, counts_b, totals.get('B', 0), 20, b_y, COLOR_TEAM_B)

    def _draw_single_panel(self, screen, title, ai_name, data, total, x, y, color):
        panel_w = 225
        h = 40
        if self.show_details: h += len(data) * 20 + 8
        s = pygame.Surface((panel_w, h), pygame.SRCALPHA)
        s.fill(COLOR_PANEL_BG)
        screen.blit(s, (x, y))
        # Barre de couleur en haut
        pygame.draw.rect(screen, color, (x, y, panel_w, 4))
        # Bordure complete
        pygame.draw.rect(screen, color, (x, y, panel_w, h), 1)
        title_surf = self.font_title.render(f"{title}: {total}", True, COLOR_TEXT)
        screen.blit(title_surf, (x + 10, y + 11))

        if self.show_details:
            y_off = 32
            for u_type, count in sorted(data.items()):
                txt_surf = self.font_ui.render(f"  {u_type}: {count}", True, (210, 200, 230))
                screen.blit(txt_surf, (x + 10, y + y_off))
                y_off += 20

    def _quick_save(self):
        try:
            with open("quicksave.pkl", "wb") as f: pickle.dump(self.game, f)
            print("💾 Sauvegardé"); pygame.display.set_caption("Age of Python - SAUVEGARDÉ")
        except Exception as e: print(f"Erreur Save: {e}")

    def _quick_load(self):
        if os.path.exists("quicksave.pkl"):
            try:
                with open("quicksave.pkl", "rb") as f:
                    loaded = pickle.load(f)
                    self.game.__dict__.update(loaded.__dict__)
                    self.map = self.game.map
                print("📂 Chargé")
            except Exception as e: print(f"Erreur Load: {e}")

    def _is_click_on_minimap(self, mx, my):
        if not self.map or not self.show_minimap or not self.show_ui_master:
            return False
        max_rows = getattr(self.map, 'rows', 120)
        max_cols = getattr(self.map, 'cols', 120)
        base_iso_w = (max_cols + max_rows) * TILE_WIDTH / 2
        base_iso_h = (max_cols + max_rows) * TILE_HEIGHT / 2
        scale = MINIMAP_WIDTH / base_iso_w
        mini_height = base_iso_h * scale
        rect_x = self.screen_w - MINIMAP_WIDTH - MINIMAP_MARGIN
        rect_y = self.screen_h - mini_height - MINIMAP_MARGIN
        return rect_x <= mx <= rect_x + MINIMAP_WIDTH and rect_y <= my <= rect_y + mini_height

    def _handle_minimap_click(self):
        if not self.map: return
        mx, my = pygame.mouse.get_pos()

        if self._is_click_on_minimap(mx, my):
            max_rows = getattr(self.map, 'rows', 120)
            max_cols = getattr(self.map, 'cols', 120)
            base_iso_w = (max_cols + max_rows) * TILE_WIDTH / 2
            base_iso_h = (max_cols + max_rows) * TILE_HEIGHT / 2
            scale = MINIMAP_WIDTH / base_iso_w
            mini_height = base_iso_h * scale
            rect_x = self.screen_w - MINIMAP_WIDTH - MINIMAP_MARGIN
            rect_y = self.screen_h - mini_height - MINIMAP_MARGIN

            rel_x = mx - rect_x
            rel_y = my - rect_y
            offset_x_world = max_rows * TILE_WIDTH / 2
            world_x = (rel_x / scale) - offset_x_world
            world_y = rel_y / scale
            self.camera_x = (self.screen_w // 2) - world_x
            self.camera_y = (self.screen_h // 2) - world_y