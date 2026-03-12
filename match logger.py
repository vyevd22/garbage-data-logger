import json
import os
from collections import defaultdict
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

#  ===========
#   CONSTANTS
#  ===========

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_FILE = os.path.join(BASE_DIR, "stats.json")
HISTORY_FILE = os.path.join(BASE_DIR, "match_history.json")

#  ===================================================================================
#   PLAYER CLASS MAKES IT SO THAT EACH PLAYER'S STATS ARE ENCAPSULATED IN AN 'OBJECT'
#       WITH METHODS TO MODIFY THEM AND CONVERT TO/FROM DICTIONARIES FOR JSON
#          RATHER THAN MANIPULATING PLAIN DICTIONARIES THROUGHOUT THE CODE
#  ===================================================================================

class Player:
    def __init__(self, name, position):
        # Runs automatically when a new Player is created
        # Sets up all the stats at zero
        self.name = name
        self.position = position
        self.apps = 0
        self.goals = 0
        self.assists = 0
        self.motm = 0
        self.clean_sheets = 0

    # --- methods that modify the player's own data ---

    def add_appearance(self):
        self.apps += 1

    def add_goal(self):
        self.goals += 1

    def add_assist(self):
        self.assists += 1

    def add_motm(self):
        self.motm += 1

    def add_clean_sheet(self):
        self.clean_sheets += 1

    def get_ga(self):
        # Returns combined goals + assists
        return self.goals + self.assists

    # --- methods for saving and loading from the JSON file ---

    def to_dict(self):
        # Converts this player object into a plain dictionary so JSON can save it
        return {
            "position": self.position,
            "apps": self.apps,
            "goals": self.goals,
            "assists": self.assists,
            "motm": self.motm,
            "clean_sheets": self.clean_sheets
        }

    @staticmethod
    def from_dict(name, data):
        # Recreates a Player object from a saved dictionary
        # Used when loading stats.json back into memory
        player = Player(name, data["position"])
        player.apps = data["apps"]
        player.goals = data["goals"]
        player.assists = data["assists"]
        player.motm = data["motm"]
        player.clean_sheets = data["clean_sheets"]
        return player

#  ================================================
#   HELPER FUNCTIONS FOR BUILDING THE MATCH REPORT
#  ================================================

def get_goal_emojis(count):
    return "⚽" * count

def get_assist_emojis(count):
    return "👟" * count

def get_suffix(count, type="goal"):
    # Returns a special label if a player scored/assisted multiple times
    if count >= 4:
        return " *ROUT*" if type == "goal" else " *ROUT OF ASSISTS*"
    elif count == 3:
        return " *HATTRICK*" if type == "goal" else " *HATTRICK OF ASSISTS*"
    elif count == 2:
        return " *BRACE*"
    return ""

#  ==========================================================================================
#   ANTHROPIC API USED TO GENERATE AUTOMATIC 'HONOURABLE MENTIONS' BASED ON THE MATCH REPORT
#                               AND THE CONSENT OF THE USER
#               (CAN BE COMMENTED OUT IF YOU DON'T WANT TO USE THIS FEATURE)
#  ==========================================================================================

def generate_mention(username, position, description):
    try:
        client = Anthropic()
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[
                {
                    "role": "user",
                    "content": f"Write a short honourable mention for a football player in a Discord match report. Position: {position}. What they did: {description}. Rules: one or two sentences maximum, no quotation marks, no preamble, do not use the player's username or any name at all, only refer to the player as 'they' or 'them'."
                }
            ]
        )
        return message.content[0].text
    except Exception:
#    If the AI fails for any particular reason (no credits, no internet, API error, etc.),
#       we don't want the whole program to crash, so I just make it skip the AI mention
#                     and let the user write their own summary manually.
        return None

#  =======================
#   LOAD & SAVE FUNCTIONS
#  =======================

def load_stats():
    # Load the stats file and convert every saved dictionary back into a Player object
    # If no file exists yet, return an empty dictionary
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            raw = json.load(f)
        # raw is a dictionary of {username: plain dictionary}
        # we convert each one back into a Player object using from_dict
        return {name: Player.from_dict(name, data) for name, data in raw.items()}
    return {}

def save_stats(players):
    # Convert every Player object back into a plain dictionary so JSON can save it
    raw = {name: player.to_dict() for name, player in players.items()}
    with open(STATS_FILE, "w") as f:
        json.dump(raw, f, indent=2)

def save_match_history(match_data):
    # Load existing history if it exists, then add the new match to it
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    else:
        history = []
    history.append(match_data)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

#  =================
#   INPUT FUNCTIONS
#  =================

def get_match_info():
    print("=== MATCH DETAILS ===")
    competition = input("Competition name: ")
    home_team = input("Home team: ")
    away_team = input("Away team: ")
    home_away_question = input("Did you play as the home team? (yes/no): ").lower()
    home_score = input("Home score: ")
    away_score = input("Away score: ")
    result = input("Result (WIN/LOSS/DRAW): ").upper()
    forfeit = input("Forfeit? (yes/no): ").lower() == "yes"
    your_team = home_team if home_away_question == "yes" else away_team
    enemy_team = away_team if home_away_question == "yes" else home_team
    return competition, home_team, away_team, home_score, away_score, result, forfeit, your_team, enemy_team

def get_lineup():
    print("\n=== TACTICAL SETUP ===")
    formation = input("Formation (e.g. 2-3-1): ")

    formation_parts = formation.split("-")
    formation_numbers = [int(part) for part in formation_parts]
    outfield_count = sum(formation_numbers)
    total_players = outfield_count + 1

    print(f"\nFormation {formation} = {outfield_count} outfield + 1 GK = {total_players} players total.")
    print("Enter position name and username for each player:\n")

    lineup = {}
    gk_name = input("GK username: ")
    lineup["GK"] = gk_name

    for i in range(outfield_count):
        position = input(f"Outfield player {i+1} position (e.g. LB, CM, CF): ")
        username = input(f"{position} username: ")
        lineup[position] = username

    return formation, lineup

def get_goals():
    goals = []
    print("\n=== LOG GOALS (type 'done' to finish) ===")

    while True:
        scorer = input("Scorer username (or 'done'): ")
        if scorer.lower() == "done":
            break

        position = input("Position: ")
        minute = int(input("Minute: "))
        assister_input = input("Assisted by (or 'none'): ")

        if assister_input.lower() != "none":
            assister = assister_input
            assister_pos = input("Assister position: ")
        else:
            assister = None
            assister_pos = None

        goals.append({
            "scorer": scorer,
            "position": position,
            "minute": minute,
            "assister": assister,
            "assister_pos": assister_pos
        })

    return goals

def get_enemy_scorers():
    enemy_scorers = []
    print("\n=== ENEMY SCORERS (type 'done' to finish) ===")

    while True:
        scorer = input("Enemy scorer username (or 'done'): ")
        if scorer.lower() == "done":
            break
        enemy_scorers.append(scorer)

    return enemy_scorers

def get_honourable_mentions():
    mentions = []
    print("\n=== HONOURABLE MENTIONS (type 'done' to finish) ===")

    while True:
        username = input("Username (or 'done'): ")
        if username.lower() == "done":
            break
        position = input("Position: ")
        description = input("What did they do well? (describe freely): ")
        print("Generating mention...")
        ai_note = generate_mention(username, position, description)
        if ai_note:
            # AI succeeded — show the result and let the user decide
            print(f"\nClaude generated: {ai_note}\n")
            use_ai = input("Use this? (yes/no): ").lower() == "yes"
            note = ai_note if use_ai else input("Write your own note: ")
        else:
            # AI failed (no credits, no internet, etc.) — fall back to manual
            print("Anthropic API unavailable, switching to manual input.")
            note = input("Write your own note: ")
        mentions.append({
            "username": username,
            "position": position,
            "note": note
        })

    return mentions

def get_motm():
    return input("\nMan of the Match username: ")

#  =================
#   DATA PROCESSING
#  =================

def group_scorers(goals):
    scorers = defaultdict(lambda: {"position": "", "minutes": []})
    for goal in goals:
        scorers[goal["scorer"]]["position"] = goal["position"]
        scorers[goal["scorer"]]["minutes"].append(goal["minute"])
    return scorers

def group_assisters(goals):
    assisters = defaultdict(lambda: {"position": "", "minutes": []})
    for goal in goals:
        if goal["assister"]:
            assisters[goal["assister"]]["position"] = goal["assister_pos"]
            assisters[goal["assister"]]["minutes"].append(goal["minute"])
    return assisters

#  ================
#   REPORT BUILDER
#  ================

def build_report(competition, home_team, away_team, your_team, enemy_team, home_score, away_score,
                 result, forfeit, formation, lineup, scorers, assisters,
                 enemy_scorers, mentions, motm):

    result_text = f"{result} + FORFEIT" if forfeit else result
    lineup_parts = [f"`{pos}` - {name}" for pos, name in lineup.items()]
    lineup_str = " | ".join(lineup_parts)

    lines = []
    lines.append(f"> ## *{competition} Result‼️* || @everyone ||")
    lines.append(f"> ### HOME [{home_team}] {home_score} - {away_score} [{away_team}] AWAY")
    lines.append(f"> # {your_team} vs {enemy_team}")
    lines.append(f"-# ***{home_score}-{away_score} [ {result_text} ]***")
    lines.append(f"")
    lines.append(f"> ### __TACTICAL SETUP__:")
    lines.append(f"-# **Formation - `{formation}`**")
    lines.append(f"-# **Lineup - [ | {lineup_str} | ]**")
    lines.append(f"")
    lines.append(f"> ### __SCORERS__:")
    for name, data in scorers.items():
        goal_count = len(data["minutes"])
        minutes_str = ", ".join(str(m) + "'" for m in sorted(data["minutes"]))
        suffix = get_suffix(goal_count, "goal")
        emojis = get_goal_emojis(goal_count)
        lines.append(f"-# - **{name} [{data['position']}] - {emojis} {minutes_str}{suffix}**")

    lines.append(f"")
    lines.append(f"> ### __ASSISTERS__:")
    for name, data in assisters.items():
        assist_count = len(data["minutes"])
        minutes_str = ", ".join(str(m) + "'" for m in sorted(data["minutes"]))
        suffix = get_suffix(assist_count, "assist")
        emojis = get_assist_emojis(assist_count)
        lines.append(f"-# - **{name} [{data['position']}] - {emojis} {minutes_str}{suffix}**")

    lines.append(f"")
    lines.append(f"> ### __ENEMY SCORERS__:")
    if enemy_scorers:
        for name in enemy_scorers:
            lines.append(f"-# - **{name} - ⚽**")
    else:
        lines.append(f"-# - **None - Clean sheet! 🧤**")

    lines.append(f"")
    lines.append(f"> ### __HONOURABLE MENTIONS__:")
    for mention in mentions:
        lines.append(f"-# - **{mention['username']} [{mention['position']}] - {mention['note']}**")

    lines.append(f"")
    lines.append(f"> ## __MAN OF THE MATCH__:")
    lines.append(f"> # {motm}")

    return lines

#  ======================================
#   STATS UPDATER USING 'PLAYER' OBJECTS
#  ======================================

def update_stats(players, lineup, scorers, assisters, motm, enemy_scorers):

    # Add an appearance for every player in the lineup
    # If a player doesn't exist yet, create a new Player object for them
    for position, name in lineup.items():
        if name not in players:
            players[name] = Player(name, position)
        players[name].add_appearance()

    # Add goals — each scorer tells themselves to add a goal for each minute logged
    for name, data in scorers.items():
        if name not in players:
            players[name] = Player(name, data["position"])
        for _ in range(len(data["minutes"])):
            players[name].add_goal()

    # Add assists — same pattern as goals
    for name, data in assisters.items():
        if name not in players:
            players[name] = Player(name, data["position"])
        for _ in range(len(data["minutes"])):
            players[name].add_assist()

    # Add MoTM award
    if motm in players:
        players[motm].add_motm()

    # If no enemy scored, the GK gets a clean sheet
    if not enemy_scorers:
        gk_name = lineup.get("GK")
        if gk_name and gk_name in players:
            players[gk_name].add_clean_sheet()

    return players

#  ======
#   MAIN
#  ======

def main():
    import sys
    players = load_stats()

    if "--test" in sys.argv:
        competition = "TEST_COMP"
        home_team = "TEST_HOME"
        away_team = "TEST_AWAY"
        your_team = home_team
        enemy_team = away_team
        home_score = "3"
        away_score = "1"
        result = "WIN"
        forfeit = False
        formation = "2-3-1"
        lineup = {"GK": "test_gk", "LCB": "test_lcb", "RCB": "test_rcb", "RM": "test_rm", "CM": "test_cm", "LM": "test_lm", "CF": "test_cf"}
        goals = [
            {"scorer": "test_cf", "position": "CF", "minute": 15, "assister": "test_cm", "assister_pos": "CM"},
            {"scorer": "test_cf", "position": "CF", "minute": 30, "assister": "test_rm", "assister_pos": "RM"},
            {"scorer": "test_lcb", "position": "LCB", "minute": 45, "assister": "test_gk", "assister_pos": "GK"}
        ]
        enemy_scorers = ["enemy_player1"]
        mentions = []
        motm = "test_cm"
    else:
        competition, home_team, away_team, home_score, away_score, result, forfeit, your_team, enemy_team = get_match_info()
        formation, lineup = get_lineup()
        goals = get_goals()
        enemy_scorers = get_enemy_scorers()
        mentions = get_honourable_mentions()
        motm = get_motm()

    # Process goals into grouped scorer/assister dictionaries
    scorers = group_scorers(goals)
    assisters = group_assisters(goals)

    # Build and print the Discord report
    report_lines = build_report(competition, home_team, away_team, your_team, enemy_team, home_score, away_score,
        result, forfeit, formation, lineup, scorers, assisters,
        enemy_scorers, mentions, motm)
    print("\n\n========== COPY THIS ==========\n")
    print("\n".join(report_lines))
    print("\n================================")

    # Update stats using Player objects, then save them back to JSON
    players = update_stats(players, lineup, scorers, assisters, motm, enemy_scorers)
    save_stats(players)
    print("\nStats saved.")

    # Save full match record to history
    match_record = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "competition": competition,
        "home_team": home_team,
        "away_team": away_team,
        "score": f"{home_score}-{away_score}",
        "result": f"{result} + FORFEIT" if forfeit else result,
        "formation": formation,
        "lineup": lineup,
        "goals": goals,
        "enemy_scorers": enemy_scorers,
        "honourable_mentions": mentions,
        "motm": motm
    }
    save_match_history(match_record)
    print("Match history saved.")
    input("\nPress Enter to exit...")

main()