#!/usr/bin/env python3
"""
menu_windowed.py - Version fenêtrée du menu (Wrapper de compatibilité)

Ce fichier est maintenu pour la compatibilité, mais utilise désormais
la classe MainMenu principale qui supporte le mode fenêtré nativement.
"""

from .menu import MainMenu

class MainMenuWindowed(MainMenu):
    def __init__(self):
        # On appelle le constructeur parent en mode fenêtré
        super().__init__(windowed=True)
        # On ne réimplémente rien d'autre, on hérite de tout.

def main():
    menu = MainMenuWindowed()
    menu.run()

if __name__ == "__main__":
    main()
