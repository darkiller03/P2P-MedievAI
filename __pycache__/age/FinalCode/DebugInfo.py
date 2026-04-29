"""
Debug Info Generator - Creates HTML debug reports
"""
import os
import webbrowser
from datetime import datetime
from Engine import SimpleEngine
from typing import Dict
from Generals import General

class DebugInfoGenerator:
    def __init__(self):
        self.debug_dir = os.path.join(os.path.dirname(__file__), 'debug')
        if not os.path.exists(self.debug_dir):
            os.makedirs(self.debug_dir)
    
    def generate_html(self, engine: SimpleEngine, generals: Dict[int, General]):
        """Generate HTML debug report and open it in browser"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"debug_report_{timestamp}.html"
        filepath = os.path.join(self.debug_dir, filename)
        
        html_content = self._build_html(engine, generals)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Open in browser
        webbrowser.open('file://' + os.path.abspath(filepath))
        
        return filepath
    
    def _build_html(self, engine: SimpleEngine, generals: Dict[int, General]):
        """Build the HTML content"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Debug Report - Tick {engine.tick:.2f}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 2px solid #ddd;
            padding-bottom: 5px;
        }}
        .summary {{
            background: white;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .summary-item {{
            display: inline-block;
            margin: 10px 20px 10px 0;
            font-size: 16px;
        }}
        .summary-item strong {{
            color: #4CAF50;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .player1 {{
            color: #d32f2f;
            font-weight: bold;
        }}
        .player2 {{
            color: #1976d2;
            font-weight: bold;
        }}
        .hp-bar {{
            display: inline-block;
            width: 100px;
            height: 15px;
            background: #ddd;
            border-radius: 3px;
            overflow: hidden;
        }}
        .hp-fill {{
            height: 100%;
            background: linear-gradient(to right, #4CAF50, #8BC34A);
            transition: width 0.3s;
        }}
        .status-alive {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .status-dead {{
            color: #f44336;
            font-weight: bold;
        }}
        .events {{
            background: white;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            max-height: 400px;
            overflow-y: auto;
        }}
        .event {{
            padding: 5px;
            border-left: 3px solid #4CAF50;
            margin: 5px 0;
            padding-left: 10px;
        }}
    </style>
</head>
<body>
    <h1>🎮 MedievAIl Debug Report</h1>
    
    <div class="summary">
        <div class="summary-item"><strong>Tick:</strong> {engine.tick:.2f}</div>
        <div class="summary-item"><strong>Total Units:</strong> {len(engine.units)}</div>
        <div class="summary-item"><strong>Player 1 Units:</strong> {len(engine.get_units_for_player(1))}</div>
        <div class="summary-item"><strong>Player 2 Units:</strong> {len(engine.get_units_for_player(2))}</div>
        <div class="summary-item"><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
    </div>
    
    <h2>🎯 AI Generals</h2>
    <table>
        <tr>
            <th>Player</th>
            <th>AI Type</th>
            <th>Units Count</th>
            <th>Strategy</th>
        </tr>
"""
        
        for pid, gen in generals.items():
            unit_count = len(engine.get_units_for_player(pid))
            player_class = f"player{pid}"
            gen_type = type(gen).__name__
            strategy = self._get_strategy_description(gen_type)
            
            html += f"""
        <tr>
            <td class="{player_class}">Player {pid}</td>
            <td>{gen_type}</td>
            <td>{unit_count}</td>
            <td>{strategy}</td>
        </tr>
"""
        
        html += """
    </table>
    
    <h2>⚔️ All Units</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Player</th>
            <th>Type</th>
            <th>Position</th>
            <th>HP</th>
            <th>Attack</th>
            <th>Range</th>
            <th>Speed</th>
            <th>Target</th>
            <th>Status</th>
        </tr>
"""
        
        for u in sorted(engine.units, key=lambda x: (x.player, x.id)):
            player_class = f"player{u.player}"
            hp_percent = (u.hp / u.max_hp) * 100 if u.hp > 0 else 0
            status_class = "status-alive" if u.alive else "status-dead"
            status = "Alive" if u.alive else "Dead"
            target_info = f"Unit #{u.target_id}" if u.target_id else "None"
            
            html += f"""
        <tr>
            <td>{u.id}</td>
            <td class="{player_class}">P{u.player}</td>
            <td>{u.unit_type}</td>
            <td>({u.x:.1f}, {u.y:.1f})</td>
            <td>
                <div class="hp-bar">
                    <div class="hp-fill" style="width: {hp_percent}%"></div>
                </div>
                {u.hp:.1f} / {u.max_hp:.1f}
            </td>
            <td>{u.attack:.1f}</td>
            <td>{u.range:.1f}</td>
            <td>{u.speed:.1f}</td>
            <td>{target_info}</td>
            <td class="{status_class}">{status}</td>
        </tr>
"""
        
        html += """
    </table>
    
    <h2>📜 Recent Events</h2>
    <div class="events">
"""
        
        # Show last 50 events
        recent_events = engine.events[-50:] if len(engine.events) > 50 else engine.events
        for event in reversed(recent_events):
            html += f'        <div class="event">{event}</div>\n'
        
        html += """
    </div>
    
</body>
</html>
"""
        return html
    
    def _get_strategy_description(self, gen_type):
        """Get description of AI strategy"""
        descriptions = {
            'DaftGeneral': 'Always targets nearest enemy regardless of distance',
            'BrainDeadGeneral': 'Only attacks enemies within 5.0 range',
        }
        return descriptions.get(gen_type, 'Unknown strategy')
