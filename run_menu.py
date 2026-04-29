#!/usr/bin/env python3
"""
run_menu.py - Simple launcher for the menu with error handling
"""

import sys
import traceback

try:
    from view.menu import MainMenu

    print("Launching MedievAIl Battle Menu...")
    print("Controls:")
    print("  - Use mouse to navigate")
    print("  - ESC during battle to return to menu")
    print("  - Close window to quit")
    print("-" * 50)

    menu = MainMenu()
    menu.run()

except Exception as e:
    print("\n" + "="*50)
    print("ERROR: Menu failed to start")
    print("="*50)
    print(f"\nError message: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    print("\n" + "="*50)
    print("Possible solutions:")
    print("1. Make sure pygame is installed: pip install pygame")
    print("2. Try running in windowed mode instead of fullscreen")
    print("3. Check if display/graphics drivers are up to date")
    print("="*50)
    sys.exit(1)
