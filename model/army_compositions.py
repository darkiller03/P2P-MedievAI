"""
Module de compositions d'armées pour MedievAIl BAIttle GenerAIl

Ce module fournit différentes compositions d'armées (placement des troupes)
qui peuvent être combinées avec n'importe quel terrain.

Usage:
    from model.army_compositions import ARMY_COMPOSITIONS
    from model.terrain import TERRAIN_TYPES

    # Créer une bataille avec composition + terrain
    composition_func = ARMY_COMPOSITIONS["Standard"]
    terrain_func = TERRAIN_TYPES["colline"]
    game = composition_func(terrain_func)
"""

from model.game import Game
from model.map import BattleMap
from model.knight import Knight
from model.pikeman import Pikeman
from model.crossbowman import Crossbowman

# --- Définition des Zones (Quadrants) ---
# Format: (id) -> (min_x, max_x, min_y, max_y)
QUADRANT_BOUNDS = {
    1: (10, 50, 10, 50),    # Top-Left
    2: (70, 110, 10, 50),   # Top-Right
    3: (10, 50, 70, 110),   # Bottom-Left
    4: (70, 110, 70, 110),  # Bottom-Right
}

def spawn_army_in_quadrant(game, team, zone_id):
    """
    Génère une armée standard (27 unités) dans un quadrant spécifique.
    """
    if zone_id not in QUADRANT_BOUNDS:
        zone_id = 1
        
    x_min, x_max, y_min, y_max = QUADRANT_BOUNDS[zone_id]
    
    # Centre de la zone pour le placement relatif
    cx = (x_min + x_max) // 2
    
    # LIGNE FRONTALE : Piquiers (2 colonnes x 25 lignes = 50 unités)
    for c in range(cx + 1, cx + 3):
        for r in range(y_min + 7, y_max - 8, 1):
            game.add_unit(Pikeman(), team, row=r, col=c)
            
    # MILIEU : Chevaliers (2 colonnes x 25 lignes = 50 unités)
    for c in range(cx - 1, cx + 1):
        for r in range(y_min + 7, y_max - 8, 1):
            game.add_unit(Knight(), team, row=r, col=c)
            
    # ARRIÈRE : Arbalétriers (2 colonnes x 25 lignes = 50 unités)
    for c in range(cx - 3, cx - 1):
        for r in range(y_min + 7, y_max - 8, 1):
            game.add_unit(Crossbowman(), team, row=r, col=c)
            
    print(f"[PLACEMENT] Armée {team} placée dans la Zone {zone_id} (150 unités)")

def create_standard_armies(terrain_func=None):
    """
    Composition Standard (Rapide) - Bataille équilibrée

    Composition par équipe:
    - 50 Pikemen (première ligne)
    - 50 Knights (milieu)
    - 50 Crossbowmen (arrière)

    Total: 150 unités par équipe
    Durée: Moyenne
    """
    rows, cols = 120, 120
    battle_map = BattleMap(rows=rows, cols=cols, elevation_map=terrain_func)

    # Les contrôleurs seront définis par le menu
    game = Game(battle_map, {})

    center_r = rows // 2
    center_c = cols // 2

    # ========== ARMÉE A (Gauche) ==========
    base_col_A = center_c - 20

    # Piquiers (2 colonnes x 25 lignes = 50 unités)
    for c in range(base_col_A + 1, base_col_A + 3):
        for r in range(center_r - 12, center_r + 13, 1):
            game.add_unit(Pikeman(), "A", row=r, col=c)

    # Chevaliers (2 colonnes x 25 lignes = 50 unités)
    for c in range(base_col_A - 1, base_col_A + 1):
        for r in range(center_r - 12, center_r + 13, 1):
            game.add_unit(Knight(), "A", row=r, col=c)

    # Arbalétriers (2 colonnes x 25 lignes = 50 unités)
    for c in range(base_col_A - 3, base_col_A - 1):
        for r in range(center_r - 12, center_r + 13, 1):
            game.add_unit(Crossbowman(), "A", row=r, col=c)

    # ========== ARMÉE B (Droite) ==========
    base_col_B = center_c + 20

    # Piquiers (2 colonnes x 25 lignes = 50 unités)
    for c in range(base_col_B - 2, base_col_B):
        for r in range(center_r - 12, center_r + 13, 1):
            game.add_unit(Pikeman(), "B", row=r, col=c)

    # Chevaliers (2 colonnes x 25 lignes = 50 unités)
    for c in range(base_col_B, base_col_B + 2):
        for r in range(center_r - 12, center_r + 13, 1):
            game.add_unit(Knight(), "B", row=r, col=c)

    # Arbalétriers (2 colonnes x 25 lignes = 50 unités)
    for c in range(base_col_B + 2, base_col_B + 4):
        for r in range(center_r - 12, center_r + 13, 1):
            game.add_unit(Crossbowman(), "B", row=r, col=c)

    print(f"[COMPOSITION] Standard : {len(game.units)} unités sur {rows}x{cols}")
    return game


def create_grande_bataille(terrain_func=None):
    """
    Grande Bataille - Armées massives

    Composition par équipe:
    - 60 Pikemen (mur de piquiers)
    - 20 Knights (cavalerie lourde)
    - 25 Crossbowmen (artillerie)

    Total: ~105 unités par équipe
    Durée: Longue (10-20 minutes)
    """
    rows, cols = 120, 120
    battle_map = BattleMap(rows=rows, cols=cols, elevation_map=terrain_func)
    game = Game(battle_map, {})

    center_r = rows // 2
    center_c = cols // 2
    SPACING = 2

    # ========== ARMÉE A (Gauche) ==========
    base_col_A = center_c - 20

    # Mur de piquiers (3 colonnes × 20 lignes)
    for c in range(base_col_A + 4, base_col_A + 7):
        for r in range(center_r - 20, center_r + 20, 2):
            game.add_unit(Pikeman(), "A", row=r, col=c)

    # Chevaliers (2 colonnes × 10 lignes)
    for c in range(base_col_A, base_col_A + 3, 2):
        for r in range(center_r - 10, center_r + 10, 2):
            game.add_unit(Knight(), "A", row=r, col=c)

    # Arbalétriers (1 colonne large)
    for r in range(center_r - 25, center_r + 25, 2):
        game.add_unit(Crossbowman(), "A", row=r, col=base_col_A - 4)

    # ========== ARMÉE B (Droite) ==========
    base_col_B = center_c + 20

    # Mur de piquiers
    for c in range(base_col_B - 7, base_col_B - 4):
        for r in range(center_r - 20, center_r + 20, 2):
            game.add_unit(Pikeman(), "B", row=r, col=c)

    # Chevaliers
    for c in range(base_col_B - 3, base_col_B, 2):
        for r in range(center_r - 10, center_r + 10, 2):
            game.add_unit(Knight(), "B", row=r, col=c)

    # Arbalétriers
    for r in range(center_r - 25, center_r + 25, 2):
        game.add_unit(Crossbowman(), "B", row=r, col=base_col_B + 4)

    print(f"[COMPOSITION] Grande Bataille : {len(game.units)} unités sur {rows}x{cols}")
    return game


def create_cavalerie_lourde(terrain_func=None):
    """
    Cavalerie Lourde - Charge massive de Knights

    Composition par équipe:
    - 50 Knights (charge rapide)
    - 20 Pikemen (défense anti-cavalerie)
    - 15 Crossbowmen (support)

    Total: ~85 unités par équipe
    Tactique: Rush rapide avec knights
    """
    rows, cols = 120, 120
    battle_map = BattleMap(rows=rows, cols=cols, elevation_map=terrain_func)
    game = Game(battle_map, {})

    center_r = rows // 2
    center_c = cols // 2

    # ========== ARMÉE A (Gauche) ==========
    base_col_A = center_c - 25

    # Knights (formation large)
    for c in range(base_col_A, base_col_A + 10, 2):
        for r in range(center_r - 12, center_r + 13, 2):
            game.add_unit(Knight(), "A", row=r, col=c)

    # Pikemen (défense arrière)
    for r in range(center_r - 10, center_r + 11, 2):
        game.add_unit(Pikeman(), "A", row=r, col=base_col_A - 3)

    # Crossbowmen (support)
    for r in range(center_r - 7, center_r + 8, 2):
        game.add_unit(Crossbowman(), "A", row=r, col=base_col_A - 6)

    # ========== ARMÉE B (Droite) ==========
    base_col_B = center_c + 25

    # Knights
    for c in range(base_col_B - 10, base_col_B, 2):
        for r in range(center_r - 12, center_r + 13, 2):
            game.add_unit(Knight(), "B", row=r, col=c)

    # Pikemen
    for r in range(center_r - 10, center_r + 11, 2):
        game.add_unit(Pikeman(), "B", row=r, col=base_col_B + 3)

    # Crossbowmen
    for r in range(center_r - 7, center_r + 8, 2):
        game.add_unit(Crossbowman(), "B", row=r, col=base_col_B + 6)

    print(f"[COMPOSITION] Cavalerie Lourde : {len(game.units)} unités sur {rows}x{cols}")
    return game


def create_archers_massed(terrain_func=None):
    """
    Archers Massés - Domination à distance

    Composition par équipe:
    - 60 Crossbowmen (pluie de flèches)
    - 30 Pikemen (protection frontale)
    - 10 Knights (défense mobile)

    Total: ~100 unités par équipe
    Tactique: Contrôle à distance, défense statique
    """
    rows, cols = 120, 120
    battle_map = BattleMap(rows=rows, cols=cols, elevation_map=terrain_func)
    game = Game(battle_map, {})

    center_r = rows // 2
    center_c = cols // 2

    # ========== ARMÉE A (Gauche) ==========
    base_col_A = center_c - 25

    # Crossbowmen (3 colonnes massées)
    for c in range(base_col_A - 8, base_col_A - 2, 2):
        for r in range(center_r - 20, center_r + 21, 2):
            game.add_unit(Crossbowman(), "A", row=r, col=c)

    # Pikemen (mur défensif)
    for r in range(center_r - 15, center_r + 16, 2):
        game.add_unit(Pikeman(), "A", row=r, col=base_col_A + 2)

    # Knights (réserve mobile)
    for r in range(center_r - 5, center_r + 6, 2):
        game.add_unit(Knight(), "A", row=r, col=base_col_A + 5)

    # ========== ARMÉE B (Droite) ==========
    base_col_B = center_c + 25

    # Crossbowmen
    for c in range(base_col_B + 2, base_col_B + 8, 2):
        for r in range(center_r - 20, center_r + 21, 2):
            game.add_unit(Crossbowman(), "B", row=r, col=c)

    # Pikemen
    for r in range(center_r - 15, center_r + 16, 2):
        game.add_unit(Pikeman(), "B", row=r, col=base_col_B - 2)

    # Knights
    for r in range(center_r - 5, center_r + 6, 2):
        game.add_unit(Knight(), "B", row=r, col=base_col_B - 5)

    print(f"[COMPOSITION] Archers Massés : {len(game.units)} unités sur {rows}x{cols}")
    return game


def create_balanced_formation(terrain_func=None):
    """
    Formation Équilibrée - Mix parfait

    Composition par équipe:
    - 35 Pikemen (ligne défensive)
    - 30 Knights (force de frappe)
    - 35 Crossbowmen (support à distance)

    Total: ~100 unités par équipe
    Tactique: Polyvalente, adaptable
    """
    rows, cols = 120, 120
    battle_map = BattleMap(rows=rows, cols=cols, elevation_map=terrain_func)
    game = Game(battle_map, {})

    center_r = rows // 2
    center_c = cols // 2

    # ========== ARMÉE A (Gauche) ==========
    base_col_A = center_c - 22

    # Pikemen (2 colonnes)
    for c in range(base_col_A + 6, base_col_A + 10, 2):
        for r in range(center_r - 17, center_r + 18, 2):
            game.add_unit(Pikeman(), "A", row=r, col=c)

    # Knights (2 colonnes)
    for c in range(base_col_A + 2, base_col_A + 6, 2):
        for r in range(center_r - 15, center_r + 16, 2):
            game.add_unit(Knight(), "A", row=r, col=c)

    # Crossbowmen (2 colonnes)
    for c in range(base_col_A - 4, base_col_A + 2, 3):
        for r in range(center_r - 17, center_r + 18, 2):
            game.add_unit(Crossbowman(), "A", row=r, col=c)

    # ========== ARMÉE B (Droite) ==========
    base_col_B = center_c + 22

    # Pikemen
    for c in range(base_col_B - 10, base_col_B - 6, 2):
        for r in range(center_r - 17, center_r + 18, 2):
            game.add_unit(Pikeman(), "B", row=r, col=c)

    # Knights
    for c in range(base_col_B - 6, base_col_B - 2, 2):
        for r in range(center_r - 15, center_r + 16, 2):
            game.add_unit(Knight(), "B", row=r, col=c)

    # Crossbowmen
    for c in range(base_col_B - 2, base_col_B + 4, 3):
        for r in range(center_r - 17, center_r + 18, 2):
            game.add_unit(Crossbowman(), "B", row=r, col=c)

    print(f"[COMPOSITION] Formation Équilibrée : {len(game.units)} unités sur {rows}x{cols}")
    return game


# ============================================================
# DICTIONNAIRE DE RÉFÉRENCE (pour le menu)
# ============================================================

ARMY_COMPOSITIONS = {
    "Bataille Médiane (150/équipe)": create_standard_armies,
    "Grande Bataille (105/équipe)": create_grande_bataille,
    "Cavalerie Lourde (85/équipe)": create_cavalerie_lourde,
    "Archers Massés (100/équipe)": create_archers_massed,
    "Formation Équilibrée (100/équipe)": create_balanced_formation,
}

COMPOSITION_DESCRIPTIONS = {
    "Bataille Médiane (150/équipe)": "Moyen - 50 Pikemen, 50 Knights, 50 Crossbowmen",
    "Grande Bataille (105/équipe)": "Épique - 60 Pikemen, 20 Knights, 25 Crossbowmen",
    "Cavalerie Lourde (85/équipe)": "Rush - 50 Knights, 20 Pikemen, 15 Crossbowmen",
    "Archers Massés (100/équipe)": "Distance - 60 Crossbowmen, 30 Pikemen, 10 Knights",
    "Formation Équilibrée (100/équipe)": "Polyvalente - 35 de chaque type",
}
