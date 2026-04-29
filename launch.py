#!/usr/bin/env python3
"""
launch.py - Main launcher for MedievAIl Battle Simulator

This script provides a simple way to launch the game with the MVP architecture.
"""

import sys

def show_menu():
    print("=" * 50)
    print("  MedievAIl BAIttle GenerAIl - Launcher")
    print("=" * 50)
    print("\nAvailable modes:")
    print("  1. GUI Menu - Fullscreen (Recommended)")
    print("  2. GUI Menu - Windowed")
    print("  3. Visual Simulation")
    print("  4. Console Simulation")
    print("  5. Terminal View (Curses)")
    print("  6. Multiplayer P2P (New)")
    print("  7. CLI Battle (Advanced)")
    print("  8. Run Diagnostics")
    print("  0. Exit")
    print("=" * 50)

def main():
    while True:
        show_menu()
        choice = input("\nSelect mode (0-7): ").strip()

        if choice == "1":
            print("\nLaunching GUI Menu (Fullscreen)...")
            try:
                from view.menu import MainMenu
                menu = MainMenu()
                menu.run()
            except Exception as e:
                print(f"\nError: {e}")
                print("Try option 2 (Windowed mode) instead")
                input("\nPress Enter to continue...")

        elif choice == "2":
            print("\nLaunching GUI Menu (Windowed)...")
            try:
                from view.menu_windowed import MainMenuWindowed
                menu = MainMenuWindowed()
                menu.run()
            except Exception as e:
                print(f"\nError: {e}")
                input("\nPress Enter to continue...")

        elif choice == "3":
            print("\nLaunching Visual Simulation...")
            import visual_simulation
            visual_simulation.main()

        elif choice == "4":
            print("\nLaunching Console Simulation...")
            import main
            main.main()

        elif choice == "5":
            print("\nLaunching Terminal View...")
            import run_terminal
            run_terminal.main()

        elif choice == "6":
            print("\nLaunching Multiplayer Menu (Windowed)...")
            from view.menu import MainMenu
            menu = MainMenu(windowed=True)
            menu.state = "multi_setup"
            menu.run()

        elif choice == "7":
            print("\nCLI Battle Mode")
            print("Usage: python -m presenter.battle <command>")
            print("Commands: run, load, tourney, plot")
            print("\nExample: python -m presenter.battle run Scenario_Standard Daft Braindead")
            input("\nPress Enter to continue...")

        elif choice == "7":
            print("\nRunning Diagnostics...")
            import subprocess
            subprocess.run([sys.executable, "diagnose_menu.py"])
            input("\nPress Enter to continue...")

        elif choice == "0":
            print("\nGoodbye!")
            sys.exit(0)

        else:
            print("\nInvalid choice. Please try again.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
        sys.exit(0)
