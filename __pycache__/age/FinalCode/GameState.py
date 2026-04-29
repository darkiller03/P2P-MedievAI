"""
Game State Manager for save/load functionality and state serialization
"""
import json
import pickle
from dataclasses import asdict
from typing import Dict
from Engine import SimpleEngine
from Generals import General
import os

class GameStateManager:
    def __init__(self):
        self.save_dir = os.path.join(os.path.dirname(__file__), 'saves')
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
    
    def quick_save(self, engine: SimpleEngine, generals: Dict[int, General], filename='quicksave.pkl'):
        """Save the current game state"""
        save_path = os.path.join(self.save_dir, filename)
        
        # Serialize engine state
        state = {
            'engine': {
                'w': engine.w,
                'h': engine.h,
                'next_unit_id': engine.next_unit_id,
                'tick': engine.tick,
                'events': engine.events.copy(),
                'units': []
            },
            'generals': {}
        }
        
        # Save units with all their attributes
        for u in engine.units:
            unit_data = {
                'id': u.id,
                'player': u.player,
                'x': u.x,
                'y': u.y,
                'hp': u.hp,
                'attack': u.attack,
                'range': u.range,
                'speed': u.speed,
                'alive': u.alive,
                'target_id': u.target_id,
                'regen': u.regen,
                'unit_type': u.unit_type,
                'color': u.color,
            }
            # Save direction tracking if exists
            if hasattr(u, 'last_x'):
                unit_data['last_x'] = u.last_x
                unit_data['last_y'] = u.last_y
            state['engine']['units'].append(unit_data)
        
        # Save general types
        for pid, gen in generals.items():
            state['generals'][pid] = {
                'type': type(gen).__name__,
                'player': gen.player
            }
        
        # Write to file
        with open(save_path, 'wb') as f:
            pickle.dump(state, f)
        
        return True
    
    def quick_load(self, filename='quicksave.pkl'):
        """Load a saved game state"""
        save_path = os.path.join(self.save_dir, filename)
        
        if not os.path.exists(save_path):
            return None
        
        with open(save_path, 'rb') as f:
            state = pickle.load(f)
        
        return state
    
    def restore_engine(self, state, engine: SimpleEngine):
        """Restore engine state from saved data"""
        from Units import Unit
        
        engine.w = state['engine']['w']
        engine.h = state['engine']['h']
        engine.next_unit_id = state['engine']['next_unit_id']
        engine.tick = state['engine']['tick']
        engine.events = state['engine']['events'].copy()
        engine.units.clear()
        engine.units_by_id.clear()
        
        # Restore units
        for unit_data in state['engine']['units']:
            # Extract last_x, last_y before creating Unit (they're not constructor params)
            last_x = unit_data.pop('last_x', None)
            last_y = unit_data.pop('last_y', None)
            
            u = Unit(**unit_data)
            
            # Restore direction tracking if exists
            if last_x is not None:
                u.last_x = last_x
                u.last_y = last_y
            
            engine.units.append(u)
            engine.units_by_id[u.id] = u
    
    def restore_generals(self, state):
        """Restore generals from saved data"""
        # Import locally to avoid circulars at module import time
        from Generals import (
            DaftGeneral,
            BrainDeadGeneral,
            New_General_1,
            New_General_2,
            New_General_3,
            GenghisKhanPrimeGeneral,
            General,
        )

        general_map = {
            'DaftGeneral': DaftGeneral,
            'BrainDeadGeneral': BrainDeadGeneral,
            'New_General_1': New_General_1,
            'New_General_2': New_General_2,
            'New_General_3': New_General_3,
            'GenghisKhanPrimeGeneral': GenghisKhanPrimeGeneral,
        }

        generals = {}
        for pid, gen_data in state['generals'].items():
            pid = int(pid)
            gen_type = gen_data.get('type')
            gen_cls = general_map.get(gen_type, DaftGeneral)  # Safe fallback to a working AI
            generals[pid] = gen_cls(pid)

        return generals
