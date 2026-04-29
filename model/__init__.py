# model/__init__.py
"""
Model layer - Business logic and game data
Contains units, map, game engine, terrain, and scenarios
"""

from .guerrier import Guerrier
from .knight import Knight
from .pikeman import Pikeman
from .crossbowman import Crossbowman
from .wonder import Wonder
from .map import BattleMap
from .terrain import (
    terrain_colline_centrale,
    terrain_deux_camps,
    terrain_siege_chateau,
    terrain_vallee_centrale
)
from .game import Game
from .scenarios import (
    scenario_simple_vs_braindead,
    scenario_small_terminal,
    scenario_lanchester,
    scenario_bataille_colline,
    scenario_deux_camps_eleves,
    scenario_siege_chateau,
)

__all__ = [
    'Guerrier',
    'Knight',
    'Pikeman',
    'Crossbowman',
    'BattleMap',
    'terrain_colline_centrale',
    'terrain_deux_camps',
    'terrain_siege_chateau',
    'terrain_vallee_centrale',
    'Game',
    'scenario_simple_vs_braindead',
    'scenario_small_terminal',
    'scenario_lanchester',
    'scenario_bataille_colline',
    'scenario_deux_camps_eleves',
    'scenario_siege_chateau',
]
