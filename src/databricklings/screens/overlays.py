"""Modal overlays: which-key menu, cheatsheet, confirm dialog, fuzzy finder."""

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from databricklings.fuzzy import fuzzy_filter
from databricklings.widgets import ACCENT, DIM, FG, YELLOW

WHICHKEY_DELAY = 0.35


class WhichKeyModal(ModalScreen[str | None]):
    """LazyVim style leader menu, appears after a short delay, returns chosen action."""

    ACTIONS = {
        "l": ("learning path", "learning"),
        "e": ("exam simulator", "exam"),
        "d": ("quick drill", "drill"),
        "r": ("review due", "review"),
        "s": ("stats", "stats"),
        "q": ("quit", "quit"),
    }

    def compose(self) -> ComposeResult:
        """Build the hidden popup body."""
        text = Text()
        text.append("  leader\n\n", style=DIM)
        for key, (label, _) in self.ACTIONS.items():
            text.append(f"  {key} ", style=f"bold {YELLOW}")
            text.append("→ ", style=DIM)
            text.append(f"{label}\n", style=FG)
        box = Static(text, id="whichkey")
        box.display = False
        yield box

    def on_mount(self) -> None:
        """Reveal the popup after the which-key delay."""
        self.set_timer(WHICHKEY_DELAY, self.reveal)

    def reveal(self) -> None:
        """Make the popup visible."""
        if self.is_attached:
            self.query_one("#whichkey").display = True

    def on_key(self, event: events.Key) -> None:
        """Dispatch the follow-up key or close on escape/space."""
        event.stop()
        if event.key in ("escape", "space"):
            self.dismiss(None)
        elif event.key in self.ACTIONS:
            self.dismiss(self.ACTIONS[event.key][1])


class CheatsheetModal(ModalScreen[None]):
    """Full keybinding cheatsheet, opened with ? on any screen."""

    ROWS = [
        ("Movement", ""),
        ("j / k", "move down / up"),
        ("h / l", "collapse / expand, prev / next pane"),
        ("gg / G", "jump to top / bottom"),
        ("ctrl-d / ctrl-u", "half page down / up"),
        ("", ""),
        ("Actions", ""),
        ("Enter", "confirm / open / submit answer"),
        ("1-5, a-e", "pick an answer option"),
        ("space", "toggle option (multi select), mark for review (exam)"),
        ("m", "mark question for review (exam)"),
        ("n / p, ]q / [q", "next / previous question"),
        ("f", "finish exam early"),
        ("Esc", "back / close"),
        ("", ""),
        ("Global", ""),
        ("space (nav screens)", "leader menu: e l d r s q"),
        ("/", "fuzzy search in lists"),
        ("?", "this cheatsheet"),
        ("q (dashboard)", "quit"),
    ]

    def compose(self) -> ComposeResult:
        """Build the cheatsheet table."""
        text = Text()
        text.append("keybindings\n\n", style=f"bold {ACCENT}")
        for key, desc in self.ROWS:
            if not desc and key:
                text.append(f"{key}\n", style=f"bold {ACCENT}")
            elif key:
                text.append(f"  {key:<22}", style=YELLOW)
                text.append(f"{desc}\n", style=FG)
            else:
                text.append("\n")
        text.append("\n? / Esc / q to close", style=DIM)
        yield Static(text, id="cheatsheet")

    def on_key(self, event: events.Key) -> None:
        """Close on escape, question mark or q."""
        event.stop()
        if event.key in ("escape", "question_mark", "q"):
            self.dismiss(None)


class ConfirmModal(ModalScreen[bool]):
    """Yes/no confirmation, y confirms, n or escape cancels."""

    def __init__(self, message: str) -> None:
        """Store the message to display."""
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        """Build the confirm box."""
        text = Text()
        text.append(f"{self.message}\n\n", style=FG)
        text.append("y ", style=f"bold {YELLOW}")
        text.append("yes    ", style=FG)
        text.append("n / Esc ", style=f"bold {YELLOW}")
        text.append("no", style=FG)
        yield Static(text, id="confirm-box")

    def on_key(self, event: events.Key) -> None:
        """Resolve to true on y, false on n or escape."""
        event.stop()
        if event.key == "y":
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            self.dismiss(False)


class FuzzyModal(ModalScreen[object | None]):
    """Telescope-like fuzzy finder over labelled items, returns the chosen item."""

    def __init__(self, items: list, label) -> None:
        """Store items and a callable producing the display label per item."""
        super().__init__()
        self.items = items
        self.label = label
        self.matches = list(items)

    def compose(self) -> ComposeResult:
        """Build input plus result list."""
        with Vertical(id="fuzzy-box"):
            yield Input(placeholder="type to filter…", id="fuzzy-input")
            yield OptionList(id="fuzzy-list")

    def on_mount(self) -> None:
        """Focus the input and show all items."""
        self.refresh_list()
        self.query_one("#fuzzy-input", Input).focus()

    def refresh_list(self) -> None:
        """Rebuild the option list from current matches."""
        lst = self.query_one("#fuzzy-list", OptionList)
        lst.clear_options()
        for item in self.matches[:50]:
            lst.add_option(Option(self.label(item)))
        if self.matches:
            lst.highlighted = 0

    def on_input_changed(self, event: Input.Changed) -> None:
        """Refilter on every keystroke."""
        self.matches = fuzzy_filter(event.value, self.items, key=self.label)
        self.refresh_list()

    def move(self, delta: int) -> None:
        """Move the highlight in the result list."""
        lst = self.query_one("#fuzzy-list", OptionList)
        if lst.option_count:
            current = lst.highlighted or 0
            lst.highlighted = max(0, min(lst.option_count - 1, current + delta))

    def on_key(self, event: events.Key) -> None:
        """Handle navigation and selection keys around the input."""
        if event.key == "escape":
            event.stop()
            self.dismiss(None)
        elif event.key in ("ctrl+j", "down"):
            event.stop()
            self.move(1)
        elif event.key in ("ctrl+k", "up"):
            event.stop()
            self.move(-1)
        elif event.key == "enter":
            event.stop()
            lst = self.query_one("#fuzzy-list", OptionList)
            if self.matches and lst.highlighted is not None and lst.highlighted < len(self.matches):
                self.dismiss(self.matches[lst.highlighted])
            else:
                self.dismiss(None)
