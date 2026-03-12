import json
import os
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_FILE = os.path.join(BASE_DIR, "stats.json")
HISTORY_FILE = os.path.join(BASE_DIR, "match_history.json")

#  ================
#   LOAD FUNCTIONS
#  ================

def load_match_history():
    # Load the match history file and return the list of matches
    # If no file exists yet, return an empty list
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def generate_player_circles(lineup, formation):
    formation_numbers = [int(x) for x in formation.split("-")]
    outfield = [(pos, name) for pos, name in lineup.items() if pos != "GK"]
    gk_name = lineup.get("GK", "")
    
    # truncate GK name here because gk_name is already defined
    gk_display = gk_name if len(gk_name) <= 12 else gk_name[:12] + "..."
    
    rows = []
    idx = 0
    for count in formation_numbers:
        rows.append(outfield[idx:idx + count])
        idx += count
    
    total_rows = len(rows) + 1
    circles = ""

    # use gk_display instead of gk_name
    circles += f"""
    <div class="player" style="left:50%; top:90%;">
        <div class="player-name">{gk_display}</div>
        <div class="player-circle"></div>
        <div class="player-pos">GK</div>
    </div>"""

    for row_idx, row in enumerate(rows):
        y = 75 - (row_idx / (total_rows - 1)) * 65
        for col_idx, (pos, name) in enumerate(row):
            # truncate here because THIS is where name exists — inside the loop
            display_name = name if len(name) <= 12 else name[:12] + "..."
            if len(row) == 1:
                x = 50
            elif len(row) == 2:
                x = 35 + (col_idx / (len(row) - 1)) * 30
            elif len(row) == 3:
                x = 10 + (col_idx / (len(row) - 1)) * 80
            else:
                x = 10 + (col_idx / (len(row) - 1)) * 80
            circles += f"""
    <div class="player" style="left:{x}%; top:{y}%;">
        <div class="player-name">{display_name}</div>
        <div class="player-circle"></div>
        <div class="player-pos">{pos}</div>
    </div>"""

    return circles

def generate_scorers(goals):
    from collections import defaultdict
    scorers = defaultdict(list)
    for g in goals:
        scorers[g["scorer"]].append(g["minute"])
    if not scorers:
        return "<p>None</p>"
    return "".join(f"<p><b>{name}</b> - {', '.join(str(m) + chr(39) for m in mins)}</p>" for name, mins in scorers.items())

def generate_enemy_scorers(enemy_scorers):
    if not enemy_scorers:
        return "<p>Clean sheet.</p>"
    return "".join(f"<p><b>{name}</b> - ⚽</p>" for name in enemy_scorers)

def generate_assisters(goals):
    from collections import defaultdict
    assisters = defaultdict(list)
    for g in goals:
        if g["assister"]:
            assisters[g["assister"]].append(g["minute"])
    if not assisters:
        return "<p>None</p>"
    return "".join(f"<p><b>{name}</b> - {', '.join(str(m) + chr(39) for m in mins)}</p>" for name, mins in assisters.items())

def generate_mentions(mentions):
    if not mentions:
        return "<p>None</p>"
    return "".join(f"<p><b>{m['username']} [{m['position']}]</b> - {m['note']}</p>" for m in mentions)

def generate_html(match):
    home = match["home_team"]
    away = match["away_team"]
    home_score, away_score = match["score"].split("-")
    formation = match["formation"]
    lineup = match["lineup"]
    goals = match["goals"]
    enemy_scorers = match.get("enemy_scorers", [])

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{home} vs {away}</title>
    <style>
        body {{
            background-color: #150730;
            color: white;
            font-family: JetBrains Mono, monospace;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            display: flex;
            gap: 20px;
            min-height: 85vh;
        }}
        .pitch {{
            background-color: #9b8fc4;
            border: 3px solid #2d1b4e;
            width: 33vw;
            min-height: 85vh;
            position: relative;
            border-radius: 8px;
        }}
        .pitch-title {{
            text-align: center;
            font-weight: bold;
            font-size: 36px;
            color: #1a1a2e;
            padding-top: 12px;
        }}
        .player {{
            position: absolute;
            text-align: center;
            transform: translate(-50%, -50%);
        }}
        .player-circle {{
            width: 25px;
            height: 25px;
            background-color: #700F2B;
            border: 2px solid #07011A;
            border-radius: 50%;
            margin: 0 auto;
        }}
        .player-name {{
            font-size: 9px;
            color: #1a1a2e;
            font-weight: bolder;
            bottom-margin: 2px;
        }}
        .player-pos {{
            font-size: 12px;
            font-weight: bolder;
            color: #2d1b4e;
        }}
        .info-panel {{
            display: flex;
            flex-direction: column;
            gap: 15px;
            flex: 1;
        }}
        .score-box {{
            background-color: #2d1b4e;
            border: 2px solid #4a3070;
            padding: 20px;
            text-align: center;
            border-radius: 8px;
            font-size: 24px;
            font-weight: bold;
        }}
        .stats-box {{
            background-color: #2d1b4e;
            border: 2px solid #4a3070;
            padding: 15px;
            border-radius: 8px;
            display: flex;
            gap: 20px;
            flex: 1;
        }}
        .stats-column {{
            flex: 1;
        }}
        .stats-column h3 {{
            margin-top: 0;
            color: #9b8fc4;
            border-bottom: 1px solid #4a3070;
            padding-bottom: 5px;
        }}
        .mentions-box {{
            background-color: #2d1b4e;
            border: 2px solid #4a3070;
            padding: 15px;
            border-radius: 8px;
            flex: 1;
        }}
        .mentions-box h3 {{
            margin-top: 0;
            color: #9b8fc4;
            border-bottom: 1px solid #4a3070;
            padding-bottom: 5px;
        }}
    </style>
</head>
<body>
    <h2 style="text-align:center">{home} vs {away} - {match["date"]}</h2>
    <div class="container">
        <div class="pitch">
            <div class="pitch-title"><b>{match.get("your_team", home)} LINEUP</b><br><b>{formation}</b></div>
            {generate_player_circles(lineup, formation)}
        </div>
        <div class="info-panel">
            <div class="score-box">{home} {home_score} - {away_score} {away}</div>
            <div class="stats-box">
                <div class="stats-column">
                    <h3>SCORERS</h3>
                    {generate_scorers(goals)}
                </div>
                <div class="stats-column">
                    <h3>ASSISTERS</h3>
                    {generate_assisters(goals)}
                </div>
            </div>
                <div class="stats-box">
        <div class="stats-column">
            <h3>ENEMY SCORERS</h3>
            {generate_enemy_scorers(enemy_scorers)}
        </div>
    </div>
            <div class="mentions-box">
                <h3>HONOURABLE MENTIONS</h3>
                {generate_mentions(match.get("honourable_mentions", []))}
            </div>
        </div>
    </div>
</body>
</html>
"""
    return html

history = load_match_history()
if history:
    html = generate_html(history[-1])
    output_path = os.path.join(BASE_DIR, "match_report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report generated: {output_path}")
else:
    print("No matches found.")