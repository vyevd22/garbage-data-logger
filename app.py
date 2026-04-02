from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Label, Footer, DataTable, Input, Static
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.binding import Binding
import json, os, zlib, base64, subprocess
from datetime import datetime
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _clipboard_get():
    for cmd in [["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
            if r.returncode == 0:
                return r.stdout
        except Exception:
            continue
    return ""


def _clipboard_set(text):
    for cmd in [["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
        try:
            subprocess.run(cmd, input=text, text=True, timeout=1)
            return
        except Exception:
            continue
STATS_FILE = os.path.join(BASE_DIR, "stats.json")
HISTORY_FILE = os.path.join(BASE_DIR, "match_history.json")

# ========================================
#  LOGIC
# ========================================

class Player:
    def __init__(self, name, position):
        self.name = name
        self.position = position
        self.apps = 0
        self.goals = 0
        self.assists = 0
        self.motm = 0
        self.clean_sheets = 0

    def add_appearance(self): self.apps += 1
    def add_goal(self): self.goals += 1
    def add_assist(self): self.assists += 1
    def add_motm(self): self.motm += 1
    def add_clean_sheet(self): self.clean_sheets += 1
    def get_ga(self): return self.goals + self.assists

    def to_dict(self):
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
        p = Player(name, data["position"])
        p.apps = data["apps"]
        p.goals = data["goals"]
        p.assists = data["assists"]
        p.motm = data["motm"]
        p.clean_sheets = data["clean_sheets"]
        return p


def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            raw = json.load(f)
        return {name: Player.from_dict(name, data) for name, data in raw.items()}
    return {}


def save_stats(players):
    raw = {name: p.to_dict() for name, p in players.items()}
    with open(STATS_FILE, "w") as f:
        json.dump(raw, f, indent=2)


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def save_to_history(match_data):
    history = load_history()
    history.append(match_data)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def encode_match(match):
    raw = json.dumps(match, ensure_ascii=False)
    compressed = zlib.compress(raw.encode("utf-8"))
    encoded = base64.b64encode(compressed).decode("utf-8")
    return f"MATCH::{encoded}"


def decode_match(code):
    try:
        encoded = code.strip().removeprefix("MATCH::")
        compressed = base64.b64decode(encoded)
        raw = zlib.decompress(compressed).decode("utf-8")
        return json.loads(raw)
    except Exception:
        return None


# ========================================
#  SCREENS
# ========================================

class MainMenuScreen(Screen):
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("up", "focus_up", "", show=False),
        Binding("down", "focus_down", "", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-container"):
            yield Label("MATCH LOGGER", id="menu-title")
            yield Label("I don't even know why I did this.", id="menu-subtitle")
            yield Button("Log Match", id="btn-log", variant="primary")
            yield Button("Match History", id="btn-history")
            yield Button("Leaderboard", id="btn-leaderboard")
            yield Button("Import Share Code", id="btn-import")
            yield Button("Quit", id="btn-quit", variant="error")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-log":
                self.app.push_screen(LogMatchScreen())
            case "btn-history":
                self.app.push_screen(HistoryScreen())
            case "btn-leaderboard":
                self.app.push_screen(LeaderboardScreen())
            case "btn-import":
                self.app.push_screen(ImportScreen())
            case "btn-quit":
                self.app.exit()

    def action_focus_up(self):
        self.focus_previous()

    def action_focus_down(self):
        self.focus_next()

    def action_quit(self):
        self.app.exit()


# ========================================
#  LOG MATCH — single scrollable form
# ========================================

class LogMatchScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self):
        super().__init__()
        self.match_data = {}
        self.home_lineup_skipped = False
        self.away_lineup_skipped = False
        self.home_goal_count = 0
        self.away_goal_count = 0
        self.mention_count = 0

    def compose(self) -> ComposeResult:
        yield Label("Log Match", id="screen-title")
        with ScrollableContainer(id="form-container"):
            # ── MATCH DETAILS ──
            yield Label("Match Details", classes="section-header")
            yield Input(placeholder="Competition name", id="input-competition")
            yield Input(placeholder="Home team name", id="input-home")
            yield Input(placeholder="Away team name", id="input-away")

            # ── FORFEIT / BONUS GOALS ──
            yield Label("Bonus Goals (forfeit, etc.)", classes="section-header")
            yield Input(placeholder="Home bonus goals (0 if none)", id="input-home-bonus")
            yield Input(placeholder="Away bonus goals (0 if none)", id="input-away-bonus")
            yield Input(placeholder="Reason (optional)", id="input-bonus-reason")

            # ── HOME LINEUP ──
            yield Label("Home Lineup", classes="section-header")
            yield Input(placeholder="Formation (e.g. 2-3-1)", id="input-home-formation")
            with Horizontal(classes="button-row"):
                yield Button("Generate Lineup", id="btn-gen-home")
                yield Button("Skip Lineup", id="btn-skip-home")
            yield Vertical(id="home-lineup-inputs")

            # ── AWAY LINEUP ──
            yield Label("Away Lineup", classes="section-header")
            yield Input(placeholder="Formation (e.g. 2-3-1)", id="input-away-formation")
            with Horizontal(classes="button-row"):
                yield Button("Generate Lineup", id="btn-gen-away")
                yield Button("Skip Lineup", id="btn-skip-away")
            yield Vertical(id="away-lineup-inputs")

            # ── GOALS ──
            yield Label("Home Goals", classes="section-header", id="home-goals-header")
            yield Vertical(id="home-goals-list")
            yield Button("+ Add Home Goal", id="btn-add-home-goal")

            yield Label("Away Goals", classes="section-header", id="away-goals-header")
            yield Vertical(id="away-goals-list")
            yield Button("+ Add Away Goal", id="btn-add-away-goal")

            # ── MOTM & MENTIONS ──
            yield Label("Man of the Match", classes="section-header")
            yield Input(placeholder="MOTM username", id="input-motm")

            yield Label("Honourable Mentions", classes="section-header")
            yield Vertical(id="mentions-list")
            yield Button("+ Add Mention", id="btn-add-mention")

            # ── GENERATE ──
            yield Button("Generate Report", id="btn-generate", variant="primary")

        yield Footer()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "input-home":
            name = event.value or "Home"
            try:
                self.query_one("#home-goals-header", Label).update(f"{name} Goals")
                self.query_one("#btn-add-home-goal", Button).label = f"+ Add {name} Goal"
            except Exception:
                pass
        elif event.input.id == "input-away":
            name = event.value or "Away"
            try:
                self.query_one("#away-goals-header", Label).update(f"{name} Goals")
                self.query_one("#btn-add-away-goal", Button).label = f"+ Add {name} Goal"
            except Exception:
                pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        # ── LINEUP GENERATION ──
        if btn_id == "btn-gen-home":
            await self._generate_lineup("home")
        elif btn_id == "btn-skip-home":
            self.home_lineup_skipped = True
            lc = self.query_one("#home-lineup-inputs")
            await lc.remove_children()
            await lc.mount(Label("(Lineup skipped)", classes="skip-label"))
        elif btn_id == "btn-gen-away":
            await self._generate_lineup("away")
        elif btn_id == "btn-skip-away":
            self.away_lineup_skipped = True
            lc = self.query_one("#away-lineup-inputs")
            await lc.remove_children()
            await lc.mount(Label("(Lineup skipped)", classes="skip-label"))

        # ── ADD GOALS ──
        elif btn_id == "btn-add-home-goal":
            i = self.home_goal_count
            row = Horizontal(
                Input(placeholder="Scorer", id=f"hg-scorer-{i}"),
                Input(placeholder="Pos", id=f"hg-pos-{i}", classes="pos-input"),
                Input(placeholder="Min", id=f"hg-min-{i}", classes="min-input"),
                Input(placeholder="Assister", id=f"hg-assist-{i}"),
                Input(placeholder="A.Pos", id=f"hg-apos-{i}", classes="pos-input"),
                classes="goal-row",
            )
            await self.query_one("#home-goals-list").mount(row)
            self.home_goal_count += 1

        elif btn_id == "btn-add-away-goal":
            i = self.away_goal_count
            row = Horizontal(
                Input(placeholder="Scorer", id=f"ag-scorer-{i}"),
                Input(placeholder="Pos", id=f"ag-pos-{i}", classes="pos-input"),
                Input(placeholder="Min", id=f"ag-min-{i}", classes="min-input"),
                Input(placeholder="Assister", id=f"ag-assist-{i}"),
                Input(placeholder="A.Pos", id=f"ag-apos-{i}", classes="pos-input"),
                classes="goal-row",
            )
            await self.query_one("#away-goals-list").mount(row)
            self.away_goal_count += 1

        # ── ADD MENTION ──
        elif btn_id == "btn-add-mention":
            i = self.mention_count
            row = Horizontal(
                Input(placeholder="Username", id=f"mention-user-{i}"),
                Input(placeholder="Shout-out note", id=f"mention-note-{i}"),
                classes="mention-row",
            )
            await self.query_one("#mentions-list").mount(row)
            self.mention_count += 1

        # ── GENERATE REPORT ──
        elif btn_id == "btn-generate":
            self.collect_match_data()
            self.app.push_screen(ReviewScreen(self.match_data))

    async def _generate_lineup(self, side):
        formation_id = f"input-{side}-formation"
        container_id = f"{side}-lineup-inputs"
        formation = self.query_one(f"#{formation_id}", Input).value.strip()
        if not formation:
            return
        try:
            parts = [int(x) for x in formation.split("-")]
        except ValueError:
            return
        total = sum(parts) + 1
        lc = self.query_one(f"#{container_id}")
        await lc.remove_children()
        rows = []
        # GK row — pre-filled pos
        rows.append(
            Horizontal(
                Input(value="GK", id=f"{side}-pos-0", classes="lineup-pos"),
                Input(placeholder="Player name", id=f"{side}-name-0", classes="lineup-name"),
                classes="player-row",
            )
        )
        for i in range(1, total):
            rows.append(
                Horizontal(
                    Input(placeholder="Pos", id=f"{side}-pos-{i}", classes="lineup-pos"),
                    Input(placeholder="Player name", id=f"{side}-name-{i}", classes="lineup-name"),
                    classes="player-row",
                )
            )
        await lc.mount(*rows)
        if side == "home":
            self.home_lineup_skipped = False
        else:
            self.away_lineup_skipped = False

    def collect_match_data(self):
        m = {}
        m["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        m["competition"] = self.query_one("#input-competition", Input).value.strip()
        m["home_team"] = self.query_one("#input-home", Input).value.strip()
        m["away_team"] = self.query_one("#input-away", Input).value.strip()

        # Bonus goals
        try:
            home_bonus = int(self.query_one("#input-home-bonus", Input).value.strip())
        except (ValueError, Exception):
            home_bonus = 0
        try:
            away_bonus = int(self.query_one("#input-away-bonus", Input).value.strip())
        except (ValueError, Exception):
            away_bonus = 0
        bonus_reason = self.query_one("#input-bonus-reason", Input).value.strip()

        if home_bonus or away_bonus:
            m["forfeit"] = {
                "active": True,
                "team": "home" if home_bonus > away_bonus else "away",
                "bonus_goals": max(home_bonus, away_bonus),
                "home_bonus": home_bonus,
                "away_bonus": away_bonus,
                "reason": bonus_reason,
            }
        else:
            m["forfeit"] = {"active": False}

        # Home lineup
        if self.home_lineup_skipped:
            m["home_formation"] = ""
            m["home_lineup"] = {}
        else:
            try:
                m["home_formation"] = self.query_one("#input-home-formation", Input).value.strip()
            except Exception:
                m["home_formation"] = ""
            lineup = {}
            i = 0
            while True:
                try:
                    pos = self.query_one(f"#home-pos-{i}", Input).value.strip()
                    name = self.query_one(f"#home-name-{i}", Input).value.strip()
                    if pos and name:
                        lineup[pos] = name
                    i += 1
                except Exception:
                    break
            m["home_lineup"] = lineup

        # Away lineup
        if self.away_lineup_skipped:
            m["away_formation"] = ""
            m["away_lineup"] = {}
        else:
            try:
                m["away_formation"] = self.query_one("#input-away-formation", Input).value.strip()
            except Exception:
                m["away_formation"] = ""
            lineup = {}
            i = 0
            while True:
                try:
                    pos = self.query_one(f"#away-pos-{i}", Input).value.strip()
                    name = self.query_one(f"#away-name-{i}", Input).value.strip()
                    if pos and name:
                        lineup[pos] = name
                    i += 1
                except Exception:
                    break
            m["away_lineup"] = lineup

        # Home goals
        home_goals = []
        for i in range(self.home_goal_count):
            try:
                scorer = self.query_one(f"#hg-scorer-{i}", Input).value.strip()
                pos = self.query_one(f"#hg-pos-{i}", Input).value.strip()
                minute_str = self.query_one(f"#hg-min-{i}", Input).value.strip()
                minute = int(minute_str) if minute_str else 0
                assister = self.query_one(f"#hg-assist-{i}", Input).value.strip() or None
                apos = self.query_one(f"#hg-apos-{i}", Input).value.strip() or None
                if scorer:
                    home_goals.append({
                        "scorer": scorer, "position": pos, "minute": minute,
                        "assister": assister, "assister_pos": apos,
                    })
            except Exception:
                pass
        m["home_goals"] = home_goals

        # Away goals
        away_goals = []
        for i in range(self.away_goal_count):
            try:
                scorer = self.query_one(f"#ag-scorer-{i}", Input).value.strip()
                pos = self.query_one(f"#ag-pos-{i}", Input).value.strip()
                minute_str = self.query_one(f"#ag-min-{i}", Input).value.strip()
                minute = int(minute_str) if minute_str else 0
                assister = self.query_one(f"#ag-assist-{i}", Input).value.strip() or None
                apos = self.query_one(f"#ag-apos-{i}", Input).value.strip() or None
                if scorer:
                    away_goals.append({
                        "scorer": scorer, "position": pos, "minute": minute,
                        "assister": assister, "assister_pos": apos,
                    })
            except Exception:
                pass
        m["away_goals"] = away_goals

        # Score calculation
        home_score = len(home_goals) + home_bonus
        away_score = len(away_goals) + away_bonus
        m["score"] = f"{home_score}-{away_score}"

        if home_score > away_score:
            m["result"] = "HOME WIN"
        elif away_score > home_score:
            m["result"] = "AWAY WIN"
        else:
            m["result"] = "DRAW"
        if m["forfeit"]["active"]:
            reason = m["forfeit"].get("reason", "")
            m["result"] += f" + BONUS ({reason})" if reason else " + BONUS"

        # MOTM
        try:
            m["motm"] = self.query_one("#input-motm", Input).value.strip()
        except Exception:
            m["motm"] = ""

        # Honourable mentions
        mentions = []
        for i in range(self.mention_count):
            try:
                username = self.query_one(f"#mention-user-{i}", Input).value.strip()
                note = self.query_one(f"#mention-note-{i}", Input).value.strip()
                if username:
                    mentions.append({"username": username, "note": note})
            except Exception:
                pass
        m["honourable_mentions"] = mentions

        self.match_data = m

    def action_go_back(self):
        self.app.pop_screen()


# ========================================
#  REVIEW & SAVE
# ========================================

class ReviewScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, match_data: dict):
        super().__init__()
        self.match_data = match_data

    def compose(self) -> ComposeResult:
        yield Label("Review & Save", id="screen-title")
        with ScrollableContainer(id="detail-container"):
            yield Static(self.build_summary(), id="review-summary")
            yield Label("Discord Report (copy this)", classes="section-header")
            yield Static(self.build_discord_report(), id="discord-report")
            yield Label("Share Code", classes="section-header")
            yield Static(encode_match(self.match_data), id="share-code")
        with Horizontal(classes="button-row"):
            yield Button("Save Match", id="btn-save", variant="primary")
            yield Button("Back to Edit", id="btn-back-edit")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            save_to_history(self.match_data)
            players = load_stats()
            players = self.update_stats(players)
            save_stats(players)
            save_btn = self.query_one("#btn-save", Button)
            save_btn.label = "Saved!"
            save_btn.disabled = True
        elif event.button.id == "btn-back-edit":
            self.app.pop_screen()

    def build_summary(self):
        m = self.match_data
        lines = []
        lines.append(f"[bold]{m['competition']}[/bold]")
        lines.append(f"{m['home_team']}  {m['score']}  {m['away_team']}")
        lines.append(f"Result: {m['result']}")
        if m["forfeit"]["active"]:
            f = m["forfeit"]
            lines.append(f"BONUS: +{f.get('home_bonus', 0)} home, +{f.get('away_bonus', 0)} away — {f.get('reason', '')}")
        lines.append("")

        if m.get("home_lineup"):
            lines.append(f"[bold]Home Formation:[/bold] {m['home_formation']}")
            parts = [f"{p}: {n}" for p, n in m["home_lineup"].items()]
            lines.append(f"[bold]Home Lineup:[/bold] {' | '.join(parts)}")
        else:
            lines.append("[bold]Home Lineup:[/bold] (not recorded)")

        if m.get("away_lineup"):
            lines.append(f"[bold]Away Formation:[/bold] {m['away_formation']}")
            parts = [f"{p}: {n}" for p, n in m["away_lineup"].items()]
            lines.append(f"[bold]Away Lineup:[/bold] {' | '.join(parts)}")
        else:
            lines.append("[bold]Away Lineup:[/bold] (not recorded)")

        lines.append("")
        lines.append("[bold]Home Goals:[/bold]")
        if m["home_goals"]:
            scorers = defaultdict(list)
            for g in m["home_goals"]:
                scorers[g["scorer"]].append(g["minute"])
            for name, mins in scorers.items():
                lines.append(f"  {name} — {', '.join(str(mi) + chr(39) for mi in sorted(mins))}")
        else:
            lines.append("  None")

        lines.append("[bold]Away Goals:[/bold]")
        if m["away_goals"]:
            scorers = defaultdict(list)
            for g in m["away_goals"]:
                scorers[g["scorer"]].append(g["minute"])
            for name, mins in scorers.items():
                lines.append(f"  {name} — {', '.join(str(mi) + chr(39) for mi in sorted(mins))}")
        else:
            lines.append("  None")

        lines.append("")
        lines.append(f"[bold]MOTM:[/bold] {m.get('motm', 'N/A')}")

        if m.get("honourable_mentions"):
            lines.append("[bold]Honourable Mentions:[/bold]")
            for mention in m["honourable_mentions"]:
                lines.append(f"  {mention['username']} — {mention['note']}")

        return "\n".join(lines)

    def build_discord_report(self):
        m = self.match_data
        home = m["home_team"]
        away = m["away_team"]
        home_score, away_score = m["score"].split("-")

        lines = []
        lines.append(f"> ## *{m['competition']} Result* || @everyone ||")
        lines.append(f"> ### HOME [{home}] {home_score} - {away_score} [{away}] AWAY")
        lines.append(f"> # {home} vs {away}")
        lines.append(f"-# ***{m['score']} [ {m['result']} ]***")
        lines.append("")

        if m.get("home_lineup"):
            lp = " | ".join(f"`{p}` - {n}" for p, n in m["home_lineup"].items())
            lines.append(f"> ### __HOME TACTICAL SETUP__:")
            lines.append(f"-# **Formation - `{m['home_formation']}`**")
            lines.append(f"-# **Lineup - [ | {lp} | ]**")
            lines.append("")

        if m.get("away_lineup"):
            lp = " | ".join(f"`{p}` - {n}" for p, n in m["away_lineup"].items())
            lines.append(f"> ### __AWAY TACTICAL SETUP__:")
            lines.append(f"-# **Formation - `{m['away_formation']}`**")
            lines.append(f"-# **Lineup - [ | {lp} | ]**")
            lines.append("")

        def format_goals(goals, side):
            gl = []
            gl.append(f"> ### __{side} SCORERS__:")
            if goals:
                grouped = defaultdict(lambda: {"position": "", "minutes": []})
                for g in goals:
                    grouped[g["scorer"]]["position"] = g["position"]
                    grouped[g["scorer"]]["minutes"].append(g["minute"])
                for name, data in grouped.items():
                    count = len(data["minutes"])
                    mins_str = ", ".join(str(mi) + "'" for mi in sorted(data["minutes"]))
                    emojis = "\u26bd" * count
                    suffix = ""
                    if count >= 4: suffix = " *ROUT*"
                    elif count == 3: suffix = " *HATTRICK*"
                    elif count == 2: suffix = " *BRACE*"
                    gl.append(f"-# - **{name} [{data['position']}] - {emojis} {mins_str}{suffix}**")
            else:
                gl.append(f"-# - **None**")
            return gl

        def format_assists(goals, side):
            gl = []
            gl.append(f"> ### __{side} ASSISTERS__:")
            grouped = defaultdict(lambda: {"position": "", "minutes": []})
            for g in goals:
                if g.get("assister"):
                    grouped[g["assister"]]["position"] = g.get("assister_pos", "")
                    grouped[g["assister"]]["minutes"].append(g["minute"])
            if grouped:
                for name, data in grouped.items():
                    count = len(data["minutes"])
                    mins_str = ", ".join(str(mi) + "'" for mi in sorted(data["minutes"]))
                    emojis = "\U0001f45f" * count
                    suffix = ""
                    if count >= 4: suffix = " *ROUT OF ASSISTS*"
                    elif count == 3: suffix = " *HATTRICK OF ASSISTS*"
                    elif count == 2: suffix = " *BRACE*"
                    gl.append(f"-# - **{name} [{data['position']}] - {emojis} {mins_str}{suffix}**")
            else:
                gl.append(f"-# - **None**")
            return gl

        lines.extend(format_goals(m["home_goals"], "HOME"))
        lines.append("")
        lines.extend(format_assists(m["home_goals"], "HOME"))
        lines.append("")
        lines.extend(format_goals(m["away_goals"], "AWAY"))
        lines.append("")
        lines.extend(format_assists(m["away_goals"], "AWAY"))
        lines.append("")

        if m.get("honourable_mentions"):
            lines.append(f"> ### __HONOURABLE MENTIONS__:")
            for mention in m["honourable_mentions"]:
                lines.append(f"-# - **{mention['username']} \u2014 {mention['note']}**")
            lines.append("")

        lines.append(f"> ## __MAN OF THE MATCH__:")
        lines.append(f"> # {m.get('motm', 'N/A')}")

        return "\n".join(lines)

    def update_stats(self, players):
        m = self.match_data

        for lineup in [m.get("home_lineup", {}), m.get("away_lineup", {})]:
            for position, name in lineup.items():
                if name not in players:
                    players[name] = Player(name, position)
                players[name].add_appearance()

        for g in m.get("home_goals", []) + m.get("away_goals", []):
            scorer = g["scorer"]
            if scorer not in players:
                players[scorer] = Player(scorer, g.get("position", ""))
            players[scorer].add_goal()
            if g.get("assister"):
                assister = g["assister"]
                if assister not in players:
                    players[assister] = Player(assister, g.get("assister_pos", ""))
                players[assister].add_assist()

        motm = m.get("motm", "")
        if motm and motm in players:
            players[motm].add_motm()

        if len(m.get("away_goals", [])) == 0:
            gk = m.get("home_lineup", {}).get("GK")
            if gk and gk in players:
                players[gk].add_clean_sheet()
        if len(m.get("home_goals", [])) == 0:
            gk = m.get("away_lineup", {}).get("GK")
            if gk and gk in players:
                players[gk].add_clean_sheet()

        return players

    def action_go_back(self):
        self.app.pop_screen()


# ========================================
#  HISTORY
# ========================================

class HistoryScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self):
        super().__init__()
        self.matches = load_history()

    def compose(self) -> ComposeResult:
        yield Label("Match History", id="screen-title")
        if not self.matches:
            yield Label("No matches recorded yet.", id="empty-msg")
        else:
            yield DataTable(id="history-table")
        yield Button("\u2190 Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        if self.matches:
            table = self.query_one("#history-table", DataTable)
            table.cursor_type = "row"
            table.add_columns("Date", "Competition", "Match", "Score", "Result")
            for i, match in enumerate(self.matches):
                home = match.get("home_team", "?")
                away = match.get("away_team", "?")
                table.add_row(
                    match["date"],
                    match["competition"],
                    f"{home} vs {away}",
                    match["score"],
                    match.get("result", ""),
                    key=str(i),
                )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        index = int(event.row_key.value)
        self.app.push_screen(MatchDetailScreen(self.matches[index]))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

    def action_go_back(self):
        self.app.pop_screen()


# ========================================
#  LEADERBOARD
# ========================================

class LeaderboardScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self):
        super().__init__()
        self.players = load_stats()

    def compose(self) -> ComposeResult:
        yield Label("Season Leaderboard", id="screen-title")
        if not self.players:
            yield Label("No stats recorded yet.", id="empty-msg")
        else:
            yield DataTable(id="leaderboard-table")
        yield Button("\u2190 Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        if self.players:
            table = self.query_one("#leaderboard-table", DataTable)
            table.add_columns("Player", "Pos", "Apps", "Goals", "Assists", "G/A", "MOTM", "CS")
            sorted_players = sorted(
                self.players.items(),
                key=lambda x: x[1].apps,
                reverse=True,
            )
            for name, p in sorted_players:
                table.add_row(
                    name, p.position,
                    str(p.apps), str(p.goals), str(p.assists),
                    str(p.get_ga()), str(p.motm), str(p.clean_sheets),
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

    def action_go_back(self):
        self.app.pop_screen()


# ========================================
#  IMPORT
# ========================================

class ImportScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def compose(self) -> ComposeResult:
        yield Label("Import Share Code", id="screen-title")
        yield Input(placeholder="Paste MATCH:: share code here...", id="share-input")
        with Horizontal(id="import-buttons"):
            yield Button("Import", id="btn-do-import", variant="primary")
            yield Button("\u2190 Back", id="back")
        yield Label("", id="import-status")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "btn-do-import":
            self.do_import()

    def do_import(self):
        code = self.query_one("#share-input", Input).value.strip()
        status = self.query_one("#import-status", Label)
        if not code:
            status.update("No code entered.")
            return
        match = decode_match(code)
        if match is None:
            status.update("Invalid share code.")
            return
        save_to_history(match)
        home = match.get("home_team", "?")
        away = match.get("away_team", "?")
        status.update(f"Imported: {match.get('competition', '?')} \u2014 {home} vs {away}")
        self.app.push_screen(MatchDetailScreen(match))

    def action_go_back(self):
        self.app.pop_screen()


# ========================================
#  MATCH DETAIL
# ========================================

class MatchDetailScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, match_data: dict):
        super().__init__()
        self.match_data = match_data

    def compose(self) -> ComposeResult:
        m = self.match_data

        yield Label("Match Details", id="screen-title")
        with ScrollableContainer(id="detail-container"):
            yield Static(f"[bold]{m.get('competition', 'N/A')}[/bold]")
            yield Static(f"{m.get('home_team', '?')}  {m.get('score', '?')}  {m.get('away_team', '?')}")
            yield Static(f"Result: {m.get('result', 'N/A')}")
            yield Static(f"Date: {m.get('date', 'N/A')}")

            if m.get("forfeit", {}).get("active"):
                f = m["forfeit"]
                yield Static(f"Forfeit: +{f.get('bonus_goals', 0)} to {f.get('team', '?')} \u2014 {f.get('reason', '')}")

            yield Static("")

            if m.get("home_lineup"):
                yield Static(f"[bold]Home Formation:[/bold] {m.get('home_formation', 'N/A')}")
                parts = [f"{p}: {n}" for p, n in m["home_lineup"].items()]
                yield Static(f"[bold]Home Lineup:[/bold] {' | '.join(parts)}")
            else:
                yield Static("[bold]Home Lineup:[/bold] (not recorded)")

            if m.get("away_lineup"):
                yield Static(f"[bold]Away Formation:[/bold] {m.get('away_formation', 'N/A')}")
                parts = [f"{p}: {n}" for p, n in m["away_lineup"].items()]
                yield Static(f"[bold]Away Lineup:[/bold] {' | '.join(parts)}")
            else:
                yield Static("[bold]Away Lineup:[/bold] (not recorded)")

            yield Static("")

            yield Static("[bold]Home Goals:[/bold]")
            home_goals = m.get("home_goals", [])
            if home_goals:
                scorers = defaultdict(list)
                for g in home_goals:
                    scorers[g["scorer"]].append(g["minute"])
                for name, minutes in scorers.items():
                    mins_str = ", ".join(f"{mi}'" for mi in sorted(minutes))
                    yield Static(f"  {name} \u2014 {mins_str}")
            else:
                yield Static("  None")

            yield Static("[bold]Home Assisters:[/bold]")
            home_assists = defaultdict(list)
            for g in m.get("home_goals", []):
                if g.get("assister"):
                    home_assists[g["assister"]].append(g["minute"])
            if home_assists:
                for name, minutes in home_assists.items():
                    mins_str = ", ".join(f"{mi}'" for mi in sorted(minutes))
                    yield Static(f"  {name} \u2014 {mins_str}")
            else:
                yield Static("  None")

            yield Static("")

            yield Static("[bold]Away Goals:[/bold]")
            away_goals = m.get("away_goals", [])
            if away_goals:
                scorers = defaultdict(list)
                for g in away_goals:
                    scorers[g["scorer"]].append(g["minute"])
                for name, minutes in scorers.items():
                    mins_str = ", ".join(f"{mi}'" for mi in sorted(minutes))
                    yield Static(f"  {name} \u2014 {mins_str}")
            else:
                yield Static("  None")

            yield Static("[bold]Away Assisters:[/bold]")
            away_assists = defaultdict(list)
            for g in m.get("away_goals", []):
                if g.get("assister"):
                    away_assists[g["assister"]].append(g["minute"])
            if away_assists:
                for name, minutes in away_assists.items():
                    mins_str = ", ".join(f"{mi}'" for mi in sorted(minutes))
                    yield Static(f"  {name} \u2014 {mins_str}")
            else:
                yield Static("  None")

            yield Static("")

            mentions = m.get("honourable_mentions", [])
            yield Static("[bold]Honourable Mentions:[/bold]")
            if mentions:
                for mention in mentions:
                    yield Static(f"  {mention['username']} \u2014 {mention['note']}")
            else:
                yield Static("  None")

            yield Static("")
            yield Static(f"[bold]Man of the Match:[/bold] {m.get('motm', 'N/A')}")

            yield Static("")
            yield Static("[bold]Share Code:[/bold]")
            yield Static(encode_match(m))

        yield Button("\u2190 Back", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

    def action_go_back(self):
        self.app.pop_screen()


# ========================================
#  APP
# ========================================

class MatchLoggerApp(App):
    BINDINGS = [
        Binding("ctrl+v", "paste", "", show=False),
        Binding("ctrl+c", "copy_or_quit", "", show=False),
    ]

    CSS = """
    Screen {
        background: #0d1520;
        align: center middle;
    }

    #menu-container {
        width: 44;
        height: auto;
        padding: 2 4;
        border: round #1a2a45;
        background: #1a2a45;
    }

    #menu-title {
        text-align: center;
        color: #e6d47b;
        text-style: bold;
        width: 100%;
        padding: 1 0;
    }

    #menu-subtitle {
        text-align: center;
        color: #406aa0;
        width: 100%;
        margin-bottom: 2;
    }

    Button {
        width: 100%;
        margin: 0 0 1 0;
        background: #0d1520;
        color: #c8d8f0;
        border: tall #406aa0;
    }

    Button:hover {
        background: #406aa0;
        color: #e6d47b;
    }

    Button:focus {
        background: #406aa0;
        color: #e6d47b;
        border: tall #e6d47b;
    }

    Button.-primary {
        background: #406aa0;
        color: #e6d47b;
        border: tall #e6d47b;
    }

    Button.-primary:hover {
        background: #5580c0;
        color: #e6d47b;
    }

    Button.-error {
        background: #0d1520;
        color: #bb607b;
        border: tall #bb607b;
    }

    Button.-error:hover {
        background: #bb607b;
        color: #0d1520;
    }

    Button > .button--label {
        background: transparent;
        text-style: none;
    }

    Button:focus > .button--label {
        background: transparent;
        text-style: none;
    }

    Footer {
        background: #1a2a45;
        color: #406aa0;
    }

    #screen-title {
        text-align: center;
        color: #e6d47b;
        text-style: bold;
        width: 100%;
        padding: 1 0;
    }

    #empty-msg {
        text-align: center;
        color: #406aa0;
        width: 100%;
        padding: 2 0;
    }

    DataTable {
        height: 1fr;
        margin: 1 2;
    }

    #detail-container {
        height: 1fr;
        margin: 1 2;
        padding: 1 2;
    }

    Input {
        margin: 0 2 1 2;
    }

    #import-buttons {
        height: 3;
        margin: 1 2;
    }

    #import-buttons Button {
        width: 1fr;
    }

    #import-status {
        text-align: center;
        color: #406aa0;
        margin: 1 2;
    }

    #form-container {
        height: 1fr;
        margin: 0 2;
        padding: 1 2;
    }

    #home-lineup-inputs, #away-lineup-inputs,
    #home-goals-list, #away-goals-list,
    #mentions-list {
        height: auto;
        width: 100%;
    }

    .section-header {
        color: #e6d47b;
        text-style: bold;
        margin-top: 2;
        margin-bottom: 1;
    }

    .button-row {
        height: 3;
        margin: 0 0 1 0;
    }

    .button-row Button {
        width: 1fr;
    }

    .player-row {
        height: auto;
        width: 100%;
        margin: 0 0 1 0;
    }

    .lineup-pos {
        width: 9;
        margin: 0;
        text-align: center;
    }

    .lineup-name {
        width: 1fr;
        margin: 0;
    }

    .pos-input {
        max-width: 10;
        margin: 0;
    }

    .min-input {
        max-width: 8;
        margin: 0;
    }

    .goal-row {
        height: auto;
        width: 100%;
        margin: 0 0 1 0;
    }

    .goal-row Input {
        width: 1fr;
        margin: 0;
    }

    .mention-row {
        height: auto;
        width: 100%;
        margin: 0 0 1 0;
    }

    .mention-row Input {
        width: 1fr;
        margin: 0;
    }

    .skip-label {
        color: #406aa0;
        text-style: italic;
        padding: 1 0;
    }

    #review-summary {
        padding: 1 0;
    }

    #discord-report {
        padding: 1 0;
        color: #c8d8f0;
    }

    #share-code {
        padding: 1 0;
        color: #406aa0;
    }
    """

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())

    def action_paste(self) -> None:
        text = _clipboard_get()
        if not text:
            return
        focused = self.focused
        if isinstance(focused, Input):
            pos = focused.cursor_position
            focused.value = focused.value[:pos] + text + focused.value[pos:]
            focused.cursor_position = pos + len(text)

    def action_copy_or_quit(self) -> None:
        focused = self.focused
        if isinstance(focused, Input):
            _clipboard_set(focused.value)
        else:
            self.exit()


if __name__ == "__main__":
    MatchLoggerApp().run()
