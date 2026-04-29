# map.py
import math

class BattleMap:
    """
    Carte continue de taille rows x cols.
    Les unités ont des coordonnées flottantes (x, y).
    La grille ne sert QUE pour l'affichage (approximation).
    """

    def __init__(self, rows=120, cols=120, elevation_map=None):
        self.rows = rows
        self.cols = cols
        self.elevation_map = elevation_map
        # Propriété réseau des cases de la carte
        self.ownership = [["" for _ in range(cols)] for _ in range(rows)]

    def in_bounds(self, x, y):
        """Vérifie que (x, y) est dans la carte."""
        return 0.0 <= x < self.cols and 0.0 <= y < self.rows

    def get_elevation(self, x, y):
        """
        Retourne l'élévation à la position (x, y).
        Par défaut : terrain plat (elevation = 0)
        """
        if self.elevation_map is None:
            return 0.0

        # Si elevation_map est une fonction
        if callable(self.elevation_map):
            return float(self.elevation_map(x, y))

        # Si elevation_map est un dict ou une grille
        try:
            ix = int(round(x))
            iy = int(round(y))
            if hasattr(self.elevation_map, '__getitem__'):
                return float(self.elevation_map.get((ix, iy), 0.0))
        except:
            return 0.0

        return 0.0

    # --- Propriété Réseau ---

    def get_owner(self, x, y):
        """Retourne le propriétaire de la case (x, y)."""
        if not self.in_bounds(x, y):
            return None
        ix, iy = int(round(x)), int(round(y))
        # Protection supplémentaire contre les débordements d'arrondis
        ix = max(0, min(self.cols - 1, ix))
        iy = max(0, min(self.rows - 1, iy))
        return self.ownership[iy][ix]

    def set_owner(self, x, y, owner: str):
        """Définit le propriétaire de la case (x, y)."""
        if not self.in_bounds(x, y):
            return False
        ix, iy = int(round(x)), int(round(y))
        ix = max(0, min(self.cols - 1, ix))
        iy = max(0, min(self.rows - 1, iy))
        self.ownership[iy][ix] = owner
        return True

    def place_unit(self, unit, row, col):
        """
        Place initialement l'unité à la position (col, row).
        On stocke en flottant, mais row/col peuvent être des entiers.
        """
        x = float(col)
        y = float(row)
        if not self.in_bounds(x, y):
            raise ValueError("Position hors de la map")
        unit.x = x
        unit.y = y

    def move_unit(self, unit, new_x, new_y):
        """
        Déplace l'unité en coordonnées continues.
        Pas de collisions de cases ici, juste les bornes.
        """
        new_x = float(new_x)
        new_y = float(new_y)
        if not self.in_bounds(new_x, new_y):
            return False

        unit.x = new_x
        unit.y = new_y
        return True

    def distance(self, u1, u2):
        """Distance euclidienne (continue) entre deux unités."""
        dx = float(u1.x) - float(u2.x)
        dy = float(u1.y) - float(u2.y)
        return math.hypot(dx, dy)

    def print_ascii(self, units):
        """
        Affichage simple : on projette les unités sur la grille
        en arrondissant leurs coordonnées à l'entier le plus proche.
        """
        grid = [[None for _ in range(self.cols)] for _ in range(self.rows)]

        for u in units:
            r = int(round(u.y))
            c = int(round(u.x))
            if 0 <= r < self.rows and 0 <= c < self.cols:
                # Si plusieurs unités se projettent sur la même case,
                # on affiche la première (c'est juste un debug visuel)
                if grid[r][c] is None:
                    grid[r][c] = u

        for r in range(self.rows):
            row_str = ""
            for c in range(self.cols):
                u = grid[r][c]
                if u is None:
                    row_str += " . "
                else:
                    name = type(u).__name__[0]  # K / P / C
                    row_str += f" {name} "
            print(row_str)
        print()
