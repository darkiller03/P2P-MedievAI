from .game import Game
from .map import BattleMap
from .knight import Knight
from .pikeman import Pikeman
from .crossbowman import Crossbowman
from .terrain import (
    terrain_colline_centrale,
    terrain_deux_camps,
    terrain_siege_chateau,
    terrain_vallee_centrale,
)
from .wonder import Wonder

def scenario_simple_vs_braindead(controllers=None) -> Game:
    rows, cols = 120, 120
    battle_map = BattleMap(rows=rows, cols=cols)

    if controllers is None:
        from presenter.ai import MajorDaft, PredictEinstein
        controllers = {
            "A": MajorDaft("A"),
            "B": PredictEinstein("B"),
        }

    game = Game(battle_map, controllers)

    center_r = rows // 2
    center_c = cols // 2
    SPACING = 2

    base_col_A = center_c - 20

    for c in range(base_col_A + 4, base_col_A + 7):
        for r in range(center_r - 20, center_r + 20, 2):
            game.add_unit(Pikeman(), "A", row=r, col=c)
    for c in range(base_col_A, base_col_A + 3, 2):
        for r in range(center_r - 10, center_r + 10, 2):
            game.add_unit(Knight(), "A", row=r, col=c)

    for r in range(center_r - 25, center_r + 25, 2):
        game.add_unit(Crossbowman(), "A", row=r, col=base_col_A - 4)

    base_col_B = center_c + 20

    for c in range(base_col_B - 7, base_col_B - 4):
        for r in range(center_r - 20, center_r + 20, 2):
            game.add_unit(Pikeman(), "B", row=r, col=c)

    for c in range(base_col_B - 3, base_col_B, 2):
        for r in range(center_r - 10, center_r + 10, 2):
            game.add_unit(Knight(), "B", row=r, col=c)

    for r in range(center_r - 25, center_r + 25, 2):
        game.add_unit(Crossbowman(), "B", row=r, col=base_col_B + 4)

    print(f"Scénario généré : {len(game.units)} unités prêtes au combat sur {rows}x{cols}.")
    return game
def scenario_small_terminal(controllers=None) -> Game:
    rows, cols = 120, 120
    battle_map = BattleMap(rows=rows, cols=cols)

    if controllers is None:
        from presenter.ai import MajorDaft, CaptainBraindead
        controllers = {
            "A": MajorDaft("A"),
            "B": CaptainBraindead("B"),
        }

    game = Game(battle_map, controllers)

    mid_r = rows // 2
    mid_c = cols // 2

    for r in range(mid_r - 4, mid_r + 5):
        game.add_unit(Crossbowman(), "A", r, mid_c - 11)

    for r in range(mid_r - 3, mid_r + 4):
        game.add_unit(Knight(), "A", r, mid_c - 7)

    for r in range(mid_r - 5, mid_r + 6):
        game.add_unit(Pikeman(), "A", r, mid_c - 5)

    for r in range(mid_r - 5, mid_r + 6):
        game.add_unit(Pikeman(), "B", r, mid_c + 5)

    for r in range(mid_r - 3, mid_r + 4):
        game.add_unit(Knight(), "B", r, mid_c + 7)

    for r in range(mid_r - 4, mid_r + 5):
        game.add_unit(Crossbowman(), "B", r, mid_c +11 )

    print(f"Scénario 'Terminal Dense Centré' généré : {len(game.units)} unités sur {rows}x{cols}.")
    return game

def scenario_lanchester(unit_type_str: str, N: int, controllers=None) -> Game:
    """
    Crée un scénario N vs 2N pour vérifier les lois de Lanchester.
    """
    rows, cols = 120, 120
    battle_map = BattleMap(rows=rows, cols=cols)

    if controllers is None:
        from presenter.ai import MajorDaft
        controllers = {
            "A": MajorDaft("A"),
            "B": MajorDaft("B"),
        }

    game = Game(battle_map, controllers)

    unit_class = None
    if unit_type_str == "knight": unit_class = Knight
    elif unit_type_str == "pikeman": unit_class = Pikeman
    elif unit_type_str == "crossbowman": unit_class = Crossbowman
    else:
        print(f"Type inconnu '{unit_type_str}', défaut sur Pikeman")
        unit_class = Pikeman

    center_row = rows // 2
    start_col_A = 5
    line_length = 10

    for i in range(N):
        c_offset = (i % line_length) * 2
        r_offset = (i // line_length) * 2
        u = unit_class()
        game.add_unit(u, "A", center_row - 2 + r_offset, start_col_A + c_offset)

    start_col_B = cols - 5
    count_B = 2 * N

    for i in range(count_B):
        c_offset = (i % line_length) * 2
        r_offset = (i // line_length) * 2
        u = unit_class()
        game.add_unit(u, "B", center_row - 2 + r_offset, start_col_B - c_offset)

    print(f"[LANCHESTER] Scenario Lanchester (Horizontal) : {N} vs {2*N} sur map {rows}x{cols}")
    return game


def scenario_bataille_colline(controllers=None) -> Game:
    """
    Bataille pour la Colline Centrale (King of the Hill).
    Contrôler le sommet = +25% dégâts.
    """
    rows, cols = 120, 120
    battle_map = BattleMap(rows=rows, cols=cols, elevation_map=terrain_colline_centrale)

    if controllers is None:
        from presenter.smartAI import GeneralStrategus
        from presenter.ai import PredictEinstein
        controllers = {
            "A": GeneralStrategus("A"),
            "B": PredictEinstein("B"),
        }

    game = Game(battle_map, controllers)

    center_r = rows // 2
    center_c = cols // 2

    base_col_A = 20

    for r in range(center_r - 8, center_r + 8, 2):
        for c in range(base_col_A, base_col_A + 4, 2):
            game.add_unit(Knight(), "A", row=r, col=c)

    for r in range(center_r - 10, center_r + 10, 2):
        for c in range(base_col_A + 6, base_col_A + 10, 2):
            game.add_unit(Pikeman(), "A", row=r, col=c)

    for r in range(center_r - 6, center_r + 6, 2):
        for c in range(base_col_A + 12, base_col_A + 16, 2):
            game.add_unit(Crossbowman(), "A", row=r, col=c)

    base_col_B = 100

    for r in range(center_r - 8, center_r + 8, 2):
        for c in range(base_col_B, base_col_B + 4, 2):
            game.add_unit(Knight(), "B", row=r, col=c)

    for r in range(center_r - 10, center_r + 10, 2):
        for c in range(base_col_B - 10, base_col_B - 6, 2):
            game.add_unit(Pikeman(), "B", row=r, col=c)

    for r in range(center_r - 6, center_r + 6, 2):
        for c in range(base_col_B - 16, base_col_B - 12, 2):
            game.add_unit(Crossbowman(), "B", row=r, col=c)

    print(f"[COLLINE] King of the Hill : {len(game.units)} unites - Bataille pour la colline centrale!")
    return game


def scenario_deux_camps_eleves(controllers=None) -> Game:
    """
    Deux Collines Symétriques - Chaque camp sur sa colline (+1), vallée centrale (-1).
    """
    rows, cols = 120, 120
    battle_map = BattleMap(rows=rows, cols=cols, elevation_map=terrain_deux_camps)

    if controllers is None:
        from presenter.ai import AssasinJack, MajorDaft
        controllers = {
            "A": AssasinJack("A"),
            "B": MajorDaft("B"),
        }

    game = Game(battle_map, controllers)

    center_r = rows // 2

    base_col_A = 15

    for r in range(center_r - 15, center_r + 15, 2):
        game.add_unit(Pikeman(), "A", row=r, col=base_col_A + 10)

    for r in range(center_r - 8, center_r + 8, 3):
        game.add_unit(Knight(), "A", row=r, col=base_col_A + 5)

    for r in range(center_r - 18, center_r + 18, 2):
        for c in range(base_col_A - 5, base_col_A + 3, 3):
            game.add_unit(Crossbowman(), "A", row=r, col=c)

    base_col_B = 105

    for r in range(center_r - 15, center_r + 15, 2):
        game.add_unit(Pikeman(), "B", row=r, col=base_col_B - 10)

    for r in range(center_r - 8, center_r + 8, 3):
        game.add_unit(Knight(), "B", row=r, col=base_col_B - 5)

    for r in range(center_r - 18, center_r + 18, 2):
        for c in range(base_col_B - 3, base_col_B + 5, 3):
            game.add_unit(Crossbowman(), "B", row=r, col=c)

    print(f"[CAMPS] Deux Camps : {len(game.units)} unites - Guerre de position sur collines!")
    return game


def scenario_siege_chateau(controllers=None) -> Game:
    """
    Siège du Château Central - Défenseurs A (+25% dégâts) vs Attaquants B (supériorité numérique).
    """
    rows, cols = 120, 120
    battle_map = BattleMap(rows=rows, cols=cols, elevation_map=terrain_siege_chateau)

    if controllers is None:
        from presenter.ai import CaptainBraindead
        from presenter.smartAI import GeneralStrategus
        controllers = {
            "A": CaptainBraindead("A"),  # Défenseurs (passifs)
            "B": GeneralStrategus("B"),  # Attaquants (agressifs)
        }

    game = Game(battle_map, controllers)

    center_r = rows // 2
    center_c = cols // 2

    for r in range(center_r - 6, center_r + 6, 2):
        for c in range(center_c - 6, center_c + 6, 2):
            game.add_unit(Knight(), "A", row=r, col=c)

    positions_remparts = [
        (center_r - 8, center_c + i) for i in range(-8, 9, 2)
    ] + [
        (center_r + 8, center_c + i) for i in range(-8, 9, 2)
    ] + [
        (center_r + i, center_c - 8) for i in range(-6, 7, 2)
    ] + [
        (center_r + i, center_c + 8) for i in range(-6, 7, 2)
    ]

    for r, c in positions_remparts:
        game.add_unit(Crossbowman(), "A", row=r, col=c)

    for r in range(center_r - 4, center_r + 4, 2):
        game.add_unit(Pikeman(), "A", row=r, col=center_c - 10)
        game.add_unit(Pikeman(), "A", row=r, col=center_c + 10)

    for r in range(10, 30, 2):
        for c in range(center_c - 15, center_c + 15, 3):
            game.add_unit(Pikeman(), "B", row=r, col=c)

    for r in range(12, 28, 3):
        for c in range(center_c - 12, center_c + 12, 4):
            game.add_unit(Knight(), "B", row=r, col=c)

    for r in range(90, 110, 2):
        for c in range(center_c - 15, center_c + 15, 3):
            game.add_unit(Pikeman(), "B", row=r, col=c)

    for r in range(92, 108, 3):
        for c in range(center_c - 12, center_c + 12, 4):
            game.add_unit(Knight(), "B", row=r, col=c)

    for r in range(center_r - 15, center_r + 15, 3):
        for c in range(10, 30, 2):
            game.add_unit(Pikeman(), "B", row=r, col=c)

    for r in range(center_r - 12, center_r + 12, 4):
        for c in range(12, 28, 3):
            game.add_unit(Knight(), "B", row=r, col=c)

    for r in range(center_r - 15, center_r + 15, 3):
        for c in range(90, 110, 2):
            game.add_unit(Pikeman(), "B", row=r, col=c)

    for r in range(center_r - 12, center_r + 12, 4):
        for c in range(92, 108, 3):
            game.add_unit(Knight(), "B", row=r, col=c)

    for r in range(center_r - 20, center_r + 20, 5):
        game.add_unit(Crossbowman(), "B", row=r, col=5)
        game.add_unit(Crossbowman(), "B", row=r, col=115)

    for c in range(center_c - 20, center_c + 20, 5):
        game.add_unit(Crossbowman(), "B", row=5, col=c)
        game.add_unit(Crossbowman(), "B", row=115, col=c)

    print(f"[SIEGE] Siege : {len(game.units)} unites - Les defenseurs tiendront-ils le chateau ?")
    print(f"   Defenseurs (A): Position elevee (+25% degats)")
    print(f"   Attaquants (B): Superiorite numerique mais desavantage terrain (-25%)")
    return game



def scenario_wonder_duel(terrain_func=None):
    """
    Wonder Duel - Chaque camp a un Wonder à protéger derrière ses lignes.
    """
    if terrain_func is None:
        from .terrain import terrain_plat as terrain_flat
        terrain_func = terrain_flat

    rows, cols = 120, 120
    battle_map = BattleMap(rows=rows, cols=cols, elevation_map=terrain_func)

    controllers = {"A": None, "B": None}
    game = Game(battle_map, controllers)

    center_r = rows // 2
    center_c = cols // 2

    w_a = Wonder(x=60, y=5, team="A")
    game.add_unit(w_a, "A", 5, 60)

    w_b = Wonder(x=60, y=115, team="B")
    game.add_unit(w_b, "B", 115, 60)

    base_col_A = 30

    for c in range(base_col_A + 4, base_col_A + 7):
        for r in range(center_r - 20, center_r + 20, 2):
            game.add_unit(Pikeman(x=float(c), y=float(r)), "A", r, c)

    for c in range(base_col_A, base_col_A + 3, 2):
        for r in range(center_r - 10, center_r + 10, 2):
            game.add_unit(Knight(x=float(c), y=float(r)), "A", r, c)

    for r in range(center_r - 25, center_r + 25, 2):
        cx = base_col_A - 4
        game.add_unit(Crossbowman(x=float(cx), y=float(r)), "A", r, cx)

    base_col_B = cols - 30

    for c in range(base_col_B - 7, base_col_B - 4):
        for r in range(center_r - 20, center_r + 20, 2):
            game.add_unit(Pikeman(x=float(c), y=float(r)), "B", r, c)

    for c in range(base_col_B - 3, base_col_B, 2):
        for r in range(center_r - 10, center_r + 10, 2):
            game.add_unit(Knight(x=float(c), y=float(r)), "B", r, c)

    for r in range(center_r - 25, center_r + 25, 2):
        cx = base_col_B + 4
        game.add_unit(Crossbowman(x=float(cx), y=float(r)), "B", r, cx)

    print(f"[WONDER] Duel Standard+Wonder : {len(game.units)} unites.")
    return game
