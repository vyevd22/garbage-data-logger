import json
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_FILE = os.path.join(BASE_DIR, "stats.json")
HISTORY_FILE = os.path.join(BASE_DIR, "match_history.json")

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    return {}

def medal(rank):
    if rank == 0: return "🥇"
    if rank == 1: return "🥈"
    if rank == 2: return "🥉"
    return "🔹"

def plural(count, singular, plural_form):
    return singular if count == 1 else plural_form

def build_leaderboard(stats):
    players = list(stats.items())
    lines = []

    def section(title, key, filter_fn=None):
        filtered = [(n, d) for n, d in players if filter_fn(d)] if filter_fn else players
        sorted_players = sorted(filtered, key=lambda x: x[1][key], reverse=True)
        lines.append(f">")
        lines.append(f"> ### __{title}__:")
        if not sorted_players:
            lines.append(f"-# 🔹 **None yet**")
            return
        for i, (name, data) in enumerate(sorted_players):
            count = data[key]
            stats_str = {
                "apps": f"{count} {plural(count, 'Appearance', 'Appearances')}",
                "goals": f"{count} {plural(count, 'Goal', 'Goals')}",
                "assists": f"{count} {plural(count, 'Assist', 'Assists')}",
                "motm": f"{count} {plural(count, 'Man of the Match Award', 'Man of the Match Awards')}",
                "clean_sheets": f"{count} {plural(count, 'Clean Sheet', 'Clean Sheets')}",
            }[key]
            lines.append(f"-# {medal(i)} **{name} [{data['position']}] — {stats_str}**")

    section("TOP APPEARANCES", "apps")
    section("TOP SCORERS", "goals", filter_fn=lambda d: d["goals"] > 0)
    section("TOP ASSISTERS", "assists", filter_fn=lambda d: d["assists"] > 0)

    ga_sorted = sorted(
        [(n, d) for n, d in players if d["goals"] + d["assists"] > 0],
        key=lambda x: x[1]["goals"] + x[1]["assists"],
        reverse=True
    )
    lines.append(f">")
    lines.append(f"> ### __TOP G/A__:")
    if not ga_sorted:
        lines.append(f"-# 🔹 **None yet**")
    else:
        for i, (name, data) in enumerate(ga_sorted):
            ga = data["goals"] + data["assists"]
            g_str = f"{data['goals']} {plural(data['goals'], 'Goal', 'Goals')}"
            a_str = f"{data['assists']} {plural(data['assists'], 'Assist', 'Assists')}"
            lines.append(f"-# {medal(i)} **{name} [{data['position']}] — {ga} G/A ({g_str} / {a_str})**")

    section("MOTM AWARDS", "motm", filter_fn=lambda d: d["motm"] > 0)
    section("CLEAN SHEETS", "clean_sheets", filter_fn=lambda d: d["position"] == "GK" and d["clean_sheets"] > 0)

    return lines

stats = load_stats()
if not stats:
    print("No stats found.")
else:
    lines = []
    lines.append(f"> ## *Season Statistics* || @everyone ||")
    lines += build_leaderboard(stats)
    print("\n========== COPY THIS ==========\n")
    print("\n".join(lines))
    print("\n================================")
input("\nPress Enter to exit.")