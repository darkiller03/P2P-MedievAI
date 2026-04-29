import subprocess
import time
import os

def automated_visual_test():
    print("[TEST] Launching C Router (Host side)...")
    router_host = subprocess.Popen(["./reseau", "6000", "127.0.0.1", "6001"])
    
    print("[TEST] Launching C Router (Client side)...")
    # Note: On the same machine, we need different IPC ports for the second router
    # But for simplicity, let's just test if one instance can receive data if we simulate the other.
    router_client = subprocess.Popen(["./reseau", "6001", "127.0.0.1", "6000"])
    
    time.sleep(2)
    
    print("[TEST] Launching Game (Joiner) in windowed mode...")
    # We use a hack to start in 'multi_setup' and then 'Join'
    sync_hack = """
import pygame
from view.menu import MainMenu
from model.game import Game
from model.map import BattleMap
import time

pygame.init()
screen = pygame.display.set_mode((800, 600))
menu = MainMenu()
menu.screen = screen
# On force le lancement en mode JOIN
menu.launch_multiplayer(is_host=False)
"""
    with open("test_joiner.py", "w") as f:
        f.write(sync_hack)
        
    joiner_proc = subprocess.Popen(["python3", "test_joiner.py"])
    
    time.sleep(5) # Wait for GUI to load
    
    print("[TEST] Simulating Host placing an unit via direct IPC...")
    # We send a fake "army_sync" to the Joiner's router (port 6001 net -> 5001 ipc)
    # The Joiner is listening on port 5001 for its local router.
    # Its router (router_client) is listening on port 6001.
    # So if we send to 6001, it should show up in the Joiner game.
    
    import socket, json
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Payload compact
    fake_unit = {"t": "as", "u": {"A_1": {"tp": "Knight", "x": 50, "y": 50, "h": 100}}}
    payload = json.dumps(fake_unit).encode("utf-8")
    sock.sendto(payload, ("127.0.0.1", 6001))
    print(f"[TEST] Sent fake unit to Joiner: {fake_unit}")
    
    time.sleep(3)
    
    print("[TEST] Capturing screenshot of Joiner window...")
    subprocess.run(["screencapture", "-x", "test_result_sync.png"])
    
    print("[TEST] Cleaning up...")
    joiner_proc.terminate()
    router_host.terminate()
    router_client.terminate()
    
    if os.path.exists("test_result_sync.png"):
        print("[TEST] SUCCESS: Screenshot saved as test_result_sync.png")
    else:
        print("[TEST] FAILURE: Could not capture screenshot")

if __name__ == "__main__":
    automated_visual_test()
