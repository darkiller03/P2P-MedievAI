#!/usr/bin/env python3
"""
run_menu_windowed.py - Lance le menu en mode fenêtré

Utilisez ce fichier si le menu en plein écran ne fonctionne pas.
"""

import sys
import traceback

try:
    from view.menu import MainMenu

    print("Launching MedievAIl Battle Menu (Windowed Mode)...")
    print("This version runs in a window instead of fullscreen")
    print("Press F11 to toggle fullscreen if needed")
    print("-" * 50)

    menu = MainMenu(windowed=True)
    menu.run()
    
    input("Menu closed. Press Enter to exit console...")

except Exception as e:
    print("\n" + "="*50)
    print("ERROR: Menu failed to start")
    print("="*50)
    print(f"\nError message: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    print("\n" + "="*50)
    print("\n" + "="*50)
    input("Press Enter to close...")
    sys.exit(1)
