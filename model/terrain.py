"""
Module de génération de terrains avec élévation pour MedievAIl BAIttle GenerAIl

Ce module fournit différentes fonctions de terrain qui peuvent être passées
à BattleMap(elevation_map=fonction) pour créer des batailles tactiques.

Élévation et impact tactique:
- Niveau +1 (élevé) : k_elev = 1.25 → +25% de dégâts
- Niveau  0 (plat)  : k_elev = 1.00 → dégâts normaux
- Niveau -1 (bas)   : k_elev = 0.75 → -25% de dégâts

Utilisation:
    from terrain import terrain_colline_centrale
    battle_map = BattleMap(rows=120, cols=120, elevation_map=terrain_colline_centrale)
"""

import math
import random


def terrain_plat(x, y):
    """
    Terrain complètement plat (élévation = 0 partout).

    Tactique: Aucun avantage de position, bataille équitable.
    Cas d'usage: Scénarios de référence, tests de base.
    """
    return 0.0


def terrain_colline_centrale(x, y, map_size=120):
    """
    Colline circulaire au centre de la carte (King of the Hill).

    Structure:
    - Rayon < 15 : Sommet (+1)
    - Rayon 15-30 : Pente (0)
    - Rayon > 30 : Plaine (-1)

    Tactique: Contrôler le centre donne un avantage massif (+25% dégâts).
    L'IA doit décider entre rusher la colline ou contourner.
    """
    center = map_size / 2
    distance_from_center = math.sqrt((x - center)**2 + (y - center)**2)

    if distance_from_center < 15:
        return 1.0   # Sommet de la colline
    elif distance_from_center < 30:
        return 0.0   # Pente intermédiaire
    else:
        return -1.0  # Plaine basse


def terrain_deux_camps(x, y, map_size=120):
    """
    Deux collines symétriques (une par camp) avec vallée centrale.

    Structure:
    - x < 35 : Camp A élevé (+1)
    - x > 85 : Camp B élevé (+1)
    - 35 <= x <= 85 : Vallée centrale (-1)

    Tactique: Chaque camp commence avec avantage défensif.
    La bataille se joue dans la vallée centrale (désavantage mutuel).
    Favorise les archers (restent sur colline) vs mêlée (descend en vallée).
    """
    if x < 35:
        return 1.0   # Colline du camp A (Ouest)
    elif x > 85:
        return 1.0   # Colline du camp B (Est)
    else:
        return -1.0  # Vallée centrale (zone de combat)


def terrain_diagonale(x, y, map_size=120):
    """
    Terrain incliné en diagonale (Nord-Est élevé, Sud-Ouest bas).

    Structure:
    - x + y > 130 : Zone Nord-Est (+1)
    - x + y < 110 : Zone Sud-Ouest (-1)
    - 110 <= x + y <= 130 : Bande centrale (0)

    Tactique: Asymétrique ! Un camp commence avantagé.
    Force l'adaptation des stratégies selon position de départ.
    """
    diagonal_sum = x + y

    if diagonal_sum > 130:
        return 1.0   # Nord-Est élevé
    elif diagonal_sum < 110:
        return -1.0  # Sud-Ouest bas
    else:
        return 0.0   # Bande centrale


def terrain_vallee_centrale(x, y, map_size=120):
    """
    Vallée au centre, bordures élevées (inverse de colline_centrale).

    Structure:
    - Rayon < 20 : Vallée profonde (-1)
    - Rayon 20-40 : Pente (0)
    - Rayon > 40 : Plateau élevé (+1)

    Tactique: Le centre est un piège ! Avantage aux unités périphériques.
    Les archers sur les bords dominent la vallée centrale.
    """
    center = map_size / 2
    distance_from_center = math.sqrt((x - center)**2 + (y - center)**2)

    if distance_from_center < 20:
        return -1.0  # Vallée centrale
    elif distance_from_center < 40:
        return 0.0   # Pente
    else:
        return 1.0   # Plateau périphérique


def terrain_crete_horizontale(x, y, map_size=120):
    """
    Crête horizontale (ligne élevée au centre).

    Structure:
    - 50 < y < 70 : Crête centrale (+1)
    - Reste : Plaines (0 et -1 alternés)

    Tactique: La crête est une position stratégique.
    Contrôler cette ligne donne avantage de tir sur toute la carte.
    """
    center_y = map_size / 2

    if 50 < y < 70:
        return 1.0   # Crête centrale
    elif y < 40 or y > 80:
        return -1.0  # Zones basses
    else:
        return 0.0   # Pentes


def terrain_random_collines(x, y, seed=42):
    """
    Terrain aléatoire avec collines dispersées.

    Structure: Grille 10×10 avec élévation aléatoire par secteur.

    Tactique: Imprévisible ! Force l'adaptation en temps réel.
    Les IA doivent gérer un terrain chaotique.

    Args:
        seed: Graine pour reproductibilité (même seed = même terrain)
    """
    # Diviser la carte en secteurs de 10×10
    sector_x = int(x) // 10
    sector_y = int(y) // 10

    # Seed unique par secteur
    random.seed(seed + sector_x * 1000 + sector_y)

    return random.choice([-1.0, 0.0, 1.0])


def terrain_asymetrique_ouest(x, y, map_size=120):
    """
    Camp Ouest (A) avantagé avec colline massive.

    Structure:
    - x < 50 : Colline Ouest (+1)
    - x >= 50 : Plaine Est (0)

    Tactique: Test d'équilibrage pour IA.
    Le camp A doit exploiter son avantage terrain.
    Le camp B doit compenser par tactique supérieure.
    """
    if x < 50:
        return 1.0   # Colline Ouest (avantage Camp A)
    else:
        return 0.0   # Plaine Est


def terrain_siege_chateau(x, y, map_size=120):
    """
    Château central fortifié (défenseurs élevés, attaquants en bas).

    Structure:
    - 50 < x < 70 ET 50 < y < 70 : Château (+1)
    - Rayon 30-45 du centre : Douves/Murs (0)
    - Reste : Plaines d'approche (-1)

    Tactique: Scénario de siège !
    Défenseurs au centre ont +25% dégâts.
    Attaquants doivent traverser zone désavantageuse.
    """
    center = map_size / 2
    distance_from_center = math.sqrt((x - center)**2 + (y - center)**2)

    if distance_from_center < 15:
        return 1.0   # Château central (défenseurs)
    elif distance_from_center < 30:
        return 0.0   # Zone intermédiaire (murs)
    else:
        return -1.0  # Plaines d'approche (attaquants)


# ============================================================
# DICTIONNAIRE DE RÉFÉRENCE (pour CLI/Menu)
# ============================================================

TERRAIN_TYPES = {
    "flat": terrain_plat,
    "colline": terrain_colline_centrale,
    "deux_camps": terrain_deux_camps,
    "diagonal": terrain_diagonale,
    "vallee": terrain_vallee_centrale,
    "crete": terrain_crete_horizontale,
    "random": terrain_random_collines,
    "asymetrique": terrain_asymetrique_ouest,
    "siege": terrain_siege_chateau,
}


# ============================================================
# FONCTION UTILITAIRE : Visualiser un terrain
# ============================================================

def print_terrain_preview(terrain_func, size=30):
    """
    Affiche un aperçu ASCII du terrain (utile pour debug).

    Args:
        terrain_func: Fonction de terrain à visualiser
        size: Taille de l'aperçu (par défaut 30×30)

    Exemple:
        from terrain import print_terrain_preview, terrain_colline_centrale
        print_terrain_preview(terrain_colline_centrale)
    """
    symbols = {
        -1.0: ".",  # Bas (point)
         0.0: "-",  # Moyen (tiret)
         1.0: "#",  # Élevé (dièse)
    }

    print(f"\n=== Aperçu du terrain: {terrain_func.__name__} ===\n")

    for y in range(size):
        for x in range(size):
            # Échelle pour visualiser sur 30×30 au lieu de 120×120
            scaled_x = x * 4
            scaled_y = y * 4
            elev = terrain_func(scaled_x, scaled_y)
            print(symbols.get(elev, "?"), end="")
        print()  # Nouvelle ligne

    print("\nLegende: . = Bas (-1) | - = Plat (0) | # = Eleve (+1)\n")


# ============================================================
# TEST (si exécuté directement)
# ============================================================

if __name__ == "__main__":
    print("[MAP]  Module Terrain - MedievAIl BAIttle GenerAIl\n")
    print("Terrains disponibles:")
    for i, (name, func) in enumerate(TERRAIN_TYPES.items(), 1):
        print(f"  {i}. {name:15s} - {func.__doc__.split('Tactique:')[0].strip()}")

    print("\n" + "="*60)
    print("Aperçu de quelques terrains:\n")

    # Prévisualiser 3 terrains intéressants
    print_terrain_preview(terrain_colline_centrale, size=30)
    print_terrain_preview(terrain_deux_camps, size=30)
    print_terrain_preview(terrain_siege_chateau, size=30)
