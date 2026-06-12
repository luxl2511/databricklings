"""Shared widgets: status bar, option list rendering, bar charts."""

from rich.console import Group
from rich.syntax import Syntax
from rich.text import Text
from textual.widgets import Static

ACCENT = "#7aa2f7"
GREEN = "#9ece6a"
RED = "#f7768e"
YELLOW = "#e0af68"
MAGENTA = "#bb9af7"
DIM = "#565f89"
FG = "#c0caf5"


class StatusBar(Static):
    """Two-line bottom bar with status segments and key hints."""

    def set_status(self, left: str, middle: str = "", right: str = "", hints: str = "") -> None:
        """Update the statusline segments and the hint line."""
        width = max(self.size.width, 40)
        line = Text()
        line.append(f" {left} ", style=f"bold #1a1b26 on {ACCENT}")
        line.append(f" {middle}", style=FG)
        pad = width - line.cell_len - len(right) - 2
        line.append(" " * max(pad, 1))
        line.append(f"{right} ", style=YELLOW)
        hint_line = Text(f" {hints}", style=DIM)
        self.update(Group(line, hint_line))


def render_options(
    options: list[str],
    cursor: int,
    selected: set[int],
    multi: bool,
    reveal: list[int] | None = None,
    given: set[int] | None = None,
) -> Text:
    """Render answer options with cursor, selection marks and optional reveal colors."""
    text = Text()
    for i, opt in enumerate(options):
        letter = chr(ord("a") + i)
        pointer = "▸ " if i == cursor else "  "
        if multi:
            mark = "[x]" if i in selected else "[ ]"
        else:
            mark = "(•)" if i in selected else "( )"
        style = FG
        suffix = ""
        if reveal is not None:
            if i in reveal:
                style = GREEN
                suffix = "  ✓ correct"
            elif given is not None and i in given:
                style = RED
                suffix = "  ✗ your answer"
            else:
                style = DIM
        elif i == cursor:
            style = f"bold {ACCENT}"
        text.append(pointer, style=ACCENT if i == cursor else DIM)
        text.append(f"{mark} ", style=style)
        text.append(f"{letter}) ", style=YELLOW if reveal is None else style)
        body = opt if not suffix else opt + suffix
        text.append(body, style=style)
        if i < len(options) - 1:
            text.append("\n")
    return text


def render_code(code: str, lang: str) -> Syntax:
    """Render a syntax highlighted code block."""
    return Syntax(code.rstrip("\n"), lang, theme="ansi_dark", background_color="#16161e", padding=1)


def render_bar(label: str, pct: float, width: int = 30, count_label: str = "") -> Text:
    """Render one horizontal bar with label and percentage."""
    filled = round(width * min(pct, 100) / 100)
    color = GREEN if pct >= 80 else YELLOW if pct >= 60 else RED
    text = Text()
    text.append(f"{label:<42.42} ", style=FG)
    text.append("█" * filled, style=color)
    text.append("░" * (width - filled), style="#3b4261")
    text.append(f" {pct:5.1f}%", style=color)
    if count_label:
        text.append(f"  {count_label}", style=DIM)
    return text
