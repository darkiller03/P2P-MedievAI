from Engine import SimpleEngine
import math

def square_scenario(engine: "SimpleEngine", offset=8):
    mid_x = engine.w / 2
    mid_y = engine.h / 2

    type_stats = {
        "Pikeman": {"hp": 55, "attack": 4, "reload_time": 3.0, "range": 1.0, "speed": 1.0, "tags": ["infantry"], "bonuses": {"Cavalry": 22.0}},
        "Crossbowman": {"hp": 35, "attack": 5, "reload_time": 2.0, "range": 5.0, "speed": 0.96, "tags": ["archer"]},
        "knight": {"hp": 100, "attack": 10, "reload_time": 1.8, "armor": 2, "range": 1.0, "speed": 1.35, "tags": ["Cavalry"]},
        "Monk": {"hp": 30, "attack": 0.0, "reload_time": 1.0, "range": 9.0, "speed": 0.7, "regen": 2.5, "tags": ["Monk"]},
    }

    type_colors = {
        1: {"Pikeman": (255, 100, 50), "Crossbowman": (255, 50, 50), "knight": (200, 0, 0), "Monk": (255, 150, 100)},
        2: {"Pikeman": (50, 150, 255), "Crossbowman": (100, 200, 255), "knight": (0, 100, 255), "Monk": (150, 200, 255)}
    }

    army_composition = [
        ("Pikeman", 35),    
        ("knight", 25),
        ("Crossbowman", 30),
        ("Monk", 10),
    ]

    for player in [1, 2]:
        side_dir = 1 if player == 1 else -1
        anchor_x = mid_x - (offset * side_dir)
        
        current_row_x = anchor_x
        
        for unit_type, count in army_composition:
            units_per_column = 10
            for i in range(count):
                column = i // units_per_column
                row = i % units_per_column
                
                x = current_row_x - (column * 1.2 * side_dir)
                y = (mid_y - (units_per_column / 2)) + row
                
                engine.spawn_unit(
                    player=player, 
                    x=x, 
                    y=y, 
                    unit_type=unit_type,
                    color=type_colors[player][unit_type], 
                    **type_stats[unit_type]
                )
            
            columns_used = (count // units_per_column) + 1
            current_row_x -= (columns_used * 1.5 * side_dir)

def chevron_scenario(engine: "SimpleEngine", offset=15):
    mid_x = engine.w / 2
    mid_y = engine.h / 2

    type_stats = {
        "Pikeman": {"hp": 55, "attack": 4, "reload_time": 3.0, "range": 1.0, "speed": 1.0, "tags": ["infantry"], "bonuses": {"Cavalry": 22.0}},
        "Crossbowman": {"hp": 35, "attack": 5, "reload_time": 2.0, "range": 5.0, "speed": 0.96, "tags": ["archer"]},
        "knight": {"hp": 100, "attack": 10, "reload_time": 1.8, "armor": 2, "range": 1.0, "speed": 1.35, "tags": ["Cavalry"]},
        "Monk": {"hp": 30, "attack": 0.0, "reload_time": 1.0, "range": 9.0, "speed": 0.7, "regen": 2.5, "tags": ["Monk"]},
    }

    type_colors = {
        1: {"Pikeman": (255, 100, 50), "Crossbowman": (255, 50, 50), "knight": (200, 0, 0), "Monk": (255, 150, 100)},
        2: {"Pikeman": (50, 150, 255), "Crossbowman": (100, 200, 255), "knight": (0, 100, 255), "Monk": (150, 200, 255)}
    }

    army_layers = [
        ("Pikeman", 40),     
        ("knight", 30),      
        ("Crossbowman", 20), 
        ("Monk", 0),        
    ]

    for player in [1, 2]:
        side_dir = 1 if player == 1 else -1
        anchor_x = mid_x - (offset * side_dir)
        
        current_layer_depth = 0
        
        for unit_type, count in army_layers:
            for i in range(count):
                side = 1 if i % 2 == 0 else -1
                pos_in_wing = i // 2
                x_offset = (pos_in_wing * 0.8) + (current_layer_depth * 1.5)
                
                x = anchor_x - (x_offset * side_dir)
                y = mid_y + (pos_in_wing * 0.7 * side)
                
                engine.spawn_unit(
                    player=player, 
                    x=x, 
                    y=y, 
                    unit_type=unit_type,
                    color=type_colors[player][unit_type], 
                    **type_stats[unit_type]
                )
                
            current_layer_depth += 1

def optimal_scenario(engine: "SimpleEngine", offset=12):
    mid_x = engine.w / 2
    mid_y = engine.h / 2

    type_stats = {
        "Pikeman": {"hp": 55, "attack": 4, "reload_time": 3.0, "range": 1.0, "speed": 1.0, "tags": ["infantry"], "bonuses": {"Cavalry": 22.0}},
        "Crossbowman": {"hp": 35, "attack": 5, "reload_time": 2.0, "range": 5.0, "speed": 0.96, "tags": ["archer"]},
        "knight": {"hp": 100, "attack": 10, "reload_time": 1.8, "armor": 2, "range": 1.0, "speed": 1.35, "tags": ["Cavalry"]},
        "Monk": {"hp": 30, "attack": 0.0, "reload_time": 1.0, "range": 9.0, "speed": 0.7, "regen": 2.5, "tags": ["Monk"]},
    }

    type_colors = {
        1: {"Pikeman": (255, 100, 50), "Crossbowman": (255, 50, 50), "knight": (200, 0, 0), "Monk": (255, 150, 100)},
        2: {"Pikeman": (50, 150, 255), "Crossbowman": (100, 200, 255), "knight": (0, 100, 255), "Monk": (150, 200, 255)}
    }

    for player in [1, 2]:
        side_dir = 1 if player == 1 else -1
        anchor_x = mid_x - (offset * side_dir)

        for i in range(35):
            col = i // 7
            row = i % 7
            x = anchor_x - (col * 1.1 * side_dir)
            y = (mid_y - 3.5) + row
            engine.spawn_unit(player=player, x=x, y=y, unit_type="Pikeman",
                              color=type_colors[player]["Pikeman"], **type_stats["Pikeman"])

        for i in range(30):
            col = i // 6
            row = i % 6
            x = anchor_x - (4 * side_dir) - (col * 1.1 * side_dir)
            y = (mid_y - 3) + row
            engine.spawn_unit(player=player, x=x, y=y, unit_type="Crossbowman",
                              color=type_colors[player]["Crossbowman"], **type_stats["Crossbowman"])

        for i in range(10):
            x = anchor_x - (7 * side_dir)
            y = (mid_y - 5) + i
            engine.spawn_unit(player=player, x=x, y=y, unit_type="Monk",
                              color=type_colors[player]["Monk"], **type_stats["Monk"])

        for i in range(12):
            col = i // 4
            row = i % 4
            x = anchor_x - (2 * side_dir) - (col * 1.1 * side_dir)
            y = mid_y - 12 + row
            engine.spawn_unit(player=player, x=x, y=y, unit_type="knight",
                              color=type_colors[player]["knight"], **type_stats["knight"])
        for i in range(13):
            col = i // 4
            row = i % 4
            x = anchor_x - (2 * side_dir) - (col * 1.1 * side_dir)
            y = mid_y + 8 + row
            engine.spawn_unit(player=player, x=x, y=y, unit_type="knight",
                              color=type_colors[player]["knight"], **type_stats["knight"])

def echelon_scenario(engine: "SimpleEngine", offset=10):
    mid_x = engine.w / 2
    mid_y = engine.h / 2

    type_stats = {
        "Pikeman": {"hp": 55, "attack": 4, "reload_time": 3.0, "range": 1.0, "speed": 1.0, "tags": ["infantry"], "bonuses": {"Cavalry": 22.0}},
        "Crossbowman": {"hp": 35, "attack": 5, "reload_time": 2.0, "range": 5.0, "speed": 0.96, "tags": ["archer"]},
        "knight": {"hp": 100, "attack": 10, "reload_time": 1.8, "armor": 2, "range": 1.0, "speed": 1.35, "tags": ["Cavalry"]},
        "Monk": {"hp": 30, "attack": 0.0, "reload_time": 1.0, "range": 9.0, "speed": 0.7, "regen": 2.5, "tags": ["Monk"]},
    }

    type_colors = {
        1: {"Pikeman": (255, 100, 50), "Crossbowman": (255, 50, 50), "knight": (200, 0, 0), "Monk": (255, 150, 100)},
        2: {"Pikeman": (50, 150, 255), "Crossbowman": (100, 200, 255), "knight": (0, 100, 255), "Monk": (150, 200, 255)}
    }

    # Composition variée (Total 100)
    army_structure = [
        ("knight", 40),      
        ("Pikeman", 30),     
        ("Crossbowman", 20), 
        ("Monk", 10)         
    ]

    for player in [1, 2]:
        side_dir = 1 if player == 1 else -1
        anchor_x = mid_x - (offset * side_dir)
        
        unit_idx = 0
        for unit_type, count in army_structure:
            for i in range(count):
                row = unit_idx % 10
                col = unit_idx // 10
                
                x_shift = col * 2.0
                y_shift = row + (col * 0.5)
                
                x = anchor_x - (x_shift * side_dir)
                y = (mid_y - 8) + y_shift
                
                engine.spawn_unit(
                    player=player, 
                    x=x, 
                    y=y, 
                    unit_type=unit_type,
                    color=type_colors[player][unit_type], 
                    **type_stats[unit_type]
                )
                unit_idx += 1
