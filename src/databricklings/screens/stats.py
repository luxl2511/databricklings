"""Stats dashboard: per-domain accuracy, lessons, exams, weak topics."""

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from databricklings.leitner import due_question_ids, in_review_count
from databricklings.scoring import domain_accuracy, weak_subtopics
from databricklings.widgets import ACCENT, DIM, FG, StatusBar, render_bar
from databricklings.screens.overlays import CheatsheetModal


class StatsScreen(Screen):
    """Read-only stats over the whole answer history."""

    def compose(self) -> ComposeResult:
        """Build the stats body."""
        with VerticalScroll(id="quiz-scroll"):
            yield Static(id="stats-body", classes="panel")
        yield StatusBar()

    def on_mount(self) -> None:
        """Render all stats sections."""
        app = self.app
        progress = app.progress
        text = Text()
        text.append("stats\n\n", style=f"bold {ACCENT}")
        done = sum(1 for l in app.lessons if progress.lessons.get(l.id, {}).get("completed_at"))
        text.append(f"lessons completed   {done}/{len(app.lessons)}\n", style=FG)
        text.append(f"exams taken         {len(progress.exams)}\n", style=FG)
        if progress.exams:
            last = progress.exams[-1]
            text.append(f"last exam           {last['score']}/{last['total']} ({last['pct']}%)\n", style=FG)
        text.append(f"in review queue     {in_review_count(progress)}", style=FG)
        text.append(f"  ({len(due_question_ids(progress))} due now)\n", style=DIM)
        text.append("\nall-time accuracy per domain\n", style=f"bold {ACCENT}")
        scores = {s.domain: s for s in domain_accuracy(progress, app.questions)}
        for domain in app.domains:
            s = scores.get(domain.id)
            text.append("\n")
            if s is None or s.total == 0:
                text.append(f"D{domain.id} {domain.name:<40.40} ", style=FG)
                text.append("no answers yet", style=DIM)
            else:
                text.append(render_bar(f"D{domain.id} {domain.name}", s.pct(), count_label=f"{s.correct}/{s.total}"))
        weak = sorted(weak_subtopics(progress, app.questions))
        text.append("\n\nweakest subtopics (below 70%)\n", style=f"bold {ACCENT}")
        if weak:
            for sub in weak[:10]:
                text.append(f"  · {sub}\n", style=FG)
        else:
            text.append("  none yet, answer more questions\n", style=DIM)
        self.query_one("#stats-body", Static).update(text)
        self.query_one(StatusBar).set_status("stats", "", "", "j/k ctrl-d/u scroll  Esc back  ? help")

    def on_key(self, event: events.Key) -> None:
        """Scroll and leave."""
        scroll = self.query_one("#quiz-scroll", VerticalScroll)
        key = event.key
        if key == "escape":
            event.stop()
            self.app.pop_screen()
        elif key == "j":
            event.stop()
            scroll.scroll_to(y=scroll.scroll_y + 1, animate=False)
        elif key == "k":
            event.stop()
            scroll.scroll_to(y=scroll.scroll_y - 1, animate=False)
        elif key == "ctrl+d":
            event.stop()
            scroll.scroll_to(y=scroll.scroll_y + scroll.size.height // 2, animate=False)
        elif key == "ctrl+u":
            event.stop()
            scroll.scroll_to(y=scroll.scroll_y - scroll.size.height // 2, animate=False)
        elif key == "space":
            event.stop()
            self.app.open_leader()
        elif key == "question_mark":
            event.stop()
            self.app.push_screen(CheatsheetModal())


class DrillSetupScreen(Screen):
    """Pick drill size and scope with j/k and Enter."""

    def __init__(self) -> None:
        """Initialize selection state."""
        super().__init__()
        self.cursor = 0
        self.choices: list[tuple[str, object]] = []

    def compose(self) -> ComposeResult:
        """Build the choice list."""
        yield Static(id="drill-body", classes="panel")
        yield StatusBar()

    def on_mount(self) -> None:
        """Build choices: sizes x scopes."""
        self.choices = [("10 questions · all domains", (10, None, False)), ("20 questions · all domains", (20, None, False)),
                        ("10 questions · my weak areas", (10, None, True)), ("20 questions · my weak areas", (20, None, True))]
        for domain in self.app.domains:
            self.choices.append((f"10 questions · D{domain.id} {domain.name}", (10, domain.id, False)))
        self.render_choices()
        self.query_one(StatusBar).set_status("quick drill", "", "", "j/k move  Enter start  Esc back  ? help")

    def render_choices(self) -> None:
        """Render the cursor list."""
        text = Text()
        text.append("quick drill\n\n", style=f"bold {ACCENT}")
        for i, (label, _) in enumerate(self.choices):
            pointer = "▸ " if i == self.cursor else "  "
            text.append(pointer, style=ACCENT if i == self.cursor else DIM)
            text.append(f"{label}\n", style=f"bold {ACCENT}" if i == self.cursor else FG)
        self.query_one("#drill-body", Static).update(text)

    def on_key(self, event: events.Key) -> None:
        """Navigate and start the drill."""
        key = event.key
        if key == "j":
            event.stop()
            self.cursor = min(len(self.choices) - 1, self.cursor + 1)
            self.render_choices()
        elif key == "k":
            event.stop()
            self.cursor = max(0, self.cursor - 1)
            self.render_choices()
        elif key == "G":
            event.stop()
            self.cursor = len(self.choices) - 1
            self.render_choices()
        elif key == "enter":
            event.stop()
            count, domain, weak = self.choices[self.cursor][1]
            self.app.pop_screen()
            self.app.start_drill(count, domain, weak)
        elif key == "escape":
            event.stop()
            self.app.pop_screen()
        elif key == "question_mark":
            event.stop()
            self.app.push_screen(CheatsheetModal())
