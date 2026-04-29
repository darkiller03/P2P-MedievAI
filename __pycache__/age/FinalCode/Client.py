from Map import MAP_W, MAP_H
from Generals import General
from typing import List, Dict
import argparse
from Engine import SimpleEngine
import time
def parse_args():
    p = argparse.ArgumentParser(description="Terminal-playable MedievAIl-like simulator")
    p.add_argument('--seed', type=int, default=None)
    p.add_argument('--headless', action='store_true')
    return p.parse_args()


def run_headless(engine: SimpleEngine, generals: Dict[int, General], max_ticks=60.0):
    t=0.0; dt=0.2; step=0; start=time.time()
    while t<max_ticks:
        engine.step(dt, generals)
        t+=dt; step+=1
        p1 = engine.get_units_for_player(1)
        p2 = engine.get_units_for_player(2)
        if not p1 or not p2:
            winner = 2 if p2 else (1 if p1 else 0)
            print(f"Battle ended at t={t:.1f}s steps={step}. Winner: P{winner}")
            break
    else:
        print("Battle timed out (draw).")
    print(f"Simulation took {time.time()-start:.2f}s wall time. Engine ticks: {engine.tick:.2f}")
    print("Events:")
    for e in engine.events[-20:]:
        print("  ", e)
