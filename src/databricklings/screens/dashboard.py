"""Start screen with logo, menu and which-key leader."""

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Static

from databricklings.leitner import due_question_ids
from databricklings.widgets import ACCENT, DIM, FG, YELLOW, StatusBar
from databricklings.screens.overlays import CheatsheetModal, WhichKeyModal

LOGO = r"""
     _       _        _          _      _    _ _
  __| | __ _| |_ __ _| |__  _ __(_) ___| | _| (_)_ __   __ _ ___
 / _` |/ _` | __/ _` | '_ \| '__| |/ __| |/ / | | '_ \ / _` / __|
| (_| | (_| | || (_| | |_) | |  | | (__|   <| | | | | | (_| \__ \
 \__,_|\__,_|\__\__,_|_.__/|_|  |_|\___|_|\_\_|_|_| |_|\__, |___/
                                                       |___/
"""

MENU = [
    ("l", "learning path", "guided lessons with checkpoints"),
    ("e", "exam simulator", "59 questions, 120 minutes"),
    ("d", "quick drill", "10/20 questions, by domain or weak areas"),
    ("r", "review due", "spaced repetition queue"),
    ("s", "stats", "accuracy per domain, weak topics"),
    ("q", "quit", ""),
]


class DashboardScreen(Screen):
    """LazyVim style dashboard with direct keys and a space leader menu."""

    def compose(self) -> ComposeResult:
        """Build logo, menu and status bar."""
        with Center(id="dashboard"):
            with Vertical():
                yield Static(LOGO, id="logo")
                yield Static(
                    "study app for the Databricks Certified Data Engineer Professional exam\n"
                    "unofficial, not affiliated with Databricks, Inc.",
                    id="tagline",
                )
                yield Static(id="menu")
                yield Static(id="dash-stats", classes="dim")
        yield StatusBar()

    def on_screen_resume(self) -> None:
        """Refresh counts when coming back to the dashboard."""
        self.refresh_dashboard()

    def on_mount(self) -> None:
        """Render menu and counts."""
        menu = Text()
        for key, label, desc in MENU:
            menu.append(f"   {key}  ", style=f"bold {YELLOW}")
            menu.append(f"{label:<18}", style=FG)
            menu.append(f"{desc}\n", style=DIM)
        self.query_one("#menu", Static).update(menu)
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        """Update the progress summary line and status bar."""
        app = self.app
        done = sum(
            1 for lesson in app.lessons
            if app.progress.lessons.get(lesson.id, {}).get("completed_at")
        )
        due = len(due_question_ids(app.progress))
        exams = len(app.progress.exams)
        summary = f"   lessons {done}/{len(app.lessons)}  ·  reviews due {due}  ·  exams taken {exams}"
        self.query_one("#dash-stats", Static).update(Text(summary, style=DIM))
        self.query_one(StatusBar).set_status(
            "dashboard", "", "", "space leader  l/e/d/r/s direct  ? cheatsheet  q quit"
        )

    def on_key(self, event: events.Key) -> None:
        """Dispatch menu keys and the space leader."""
        key = event.key
        actions = {"l": "learning", "e": "exam", "d": "drill", "r": "review", "s": "stats"}
        if key in actions:
            event.stop()
            self.app.run_action_name(actions[key])
        elif key == "q":
            event.stop()
            self.app.exit()
        elif key == "space":
            event.stop()
            self.app.open_leader()
        elif key == "question_mark":
            event.stop()
            self.app.push_screen(CheatsheetModal())
