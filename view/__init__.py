# view/__init__.py
"""
View layer - Presentation and user interface
Contains GUI, terminal view, and menu
"""

from .views import GUI
try:
    from .terminal_view import TerminalView
except ImportError:
    TerminalView = None
from .menu import MainMenu

__all__ = [
    'GUI',
    'TerminalView',
    'MainMenu',
]
