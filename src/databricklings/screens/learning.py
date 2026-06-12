"""Learning path tree and lesson reading screens."""

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Markdown, Static, Tree

from databricklings.models import Lesson
from databricklings.widgets import DIM, StatusBar
from databricklings.screens.overlays import CheatsheetModal, FuzzyModal

STATE_ICONS = {"done": "✓", "partial": "◐", "open": "○", "locked": "🔒"}


class LearningPathScreen(Screen):
    """Progress map: domains as branches, lessons as leaves with state icons."""

    def compose(self) -> ComposeResult:
        """Build the tree and status bar."""
        yield Tree("curriculum", id="path-tree")
        yield StatusBar()

    def on_mount(self) -> None:
        """Populate the tree."""
        self.pending_g = False
        self.rebuild()
        self.query_one("#path-tree", Tree).focus()
        self.query_one(StatusBar).set_status(
            "learning path",
            "",
            "",
            "j/k move  h/l fold  Enter open  / search  gg/G  Esc back  ? help",
        )

    def on_screen_resume(self) -> None:
        """Refresh lesson states after finishing a lesson."""
        self.rebuild()

    def rebuild(self) -> None:
        """Rebuild tree nodes from lessons and progress."""
        app = self.app
        tree = self.query_one("#path-tree", Tree)
        opened = {n.data.id for n in tree.root.children if n.is_expanded and n.data}
        tree.clear()
        tree.show_root = False
        tree.guide_depth = 3
        states = app.lesson_states()
        for domain in app.domains:
            lessons = [l for l in app.lessons if l.domain == domain.id]
            if not lessons:
                continue
            done = sum(1 for l in lessons if states[l.id] == "done")
            label = Text()
            label.append(f"D{domain.id} {domain.name}", style="bold")
            label.append(f"  {done}/{len(lessons)}  ·  {domain.weight}%", style=DIM)
            branch = tree.root.add(label, data=domain, expand=domain.id in opened or not opened)
            for lesson in lessons:
                icon = STATE_ICONS[states[lesson.id]]
                leaf_label = f"{icon} {lesson.title}"
                branch.add_leaf(leaf_label, data=lesson)
        if tree.cursor_line < 0:
            tree.cursor_line = 0

    def open_lesson(self, lesson: Lesson) -> None:
        """Open a lesson unless it is still locked."""
        if self.app.lesson_states()[lesson.id] == "locked":
            self.app.notify("complete the previous lesson first", severity="warning", timeout=2)
            return
        self.app.push_screen(LessonScreen(lesson))

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Open the selected lesson leaf."""
        event.stop()
        if isinstance(event.node.data, Lesson):
            self.open_lesson(event.node.data)

    def on_key(self, event: events.Key) -> None:
        """Vim navigation over the tree."""
        tree = self.query_one("#path-tree", Tree)
        key = event.key
        if self.pending_g and key == "g":
            event.stop()
            self.pending_g = False
            tree.cursor_line = 0
            tree.scroll_to_line(0, animate=False)
            return
        self.pending_g = False
        if key == "j":
            event.stop()
            tree.action_cursor_down()
        elif key == "k":
            event.stop()
            tree.action_cursor_up()
        elif key == "h":
            event.stop()
            node = tree.cursor_node
            if node and node.allow_expand and node.is_expanded:
                node.collapse()
            elif node and node.parent and node.parent != tree.root:
                tree.cursor_line = node.parent.line
        elif key == "l":
            event.stop()
            node = tree.cursor_node
            if node and node.allow_expand and not node.is_expanded:
                node.expand()
        elif key == "g":
            event.stop()
            self.pending_g = True
        elif key == "G":
            event.stop()
            tree.cursor_line = tree.last_line
            tree.scroll_to_line(tree.last_line, animate=False)
        elif key == "ctrl+d":
            event.stop()
            tree.cursor_line = min(tree.last_line, tree.cursor_line + 10)
        elif key == "ctrl+u":
            event.stop()
            tree.cursor_line = max(0, tree.cursor_line - 10)
        elif key == "slash":
            event.stop()
            self.open_search()
        elif key == "escape":
            event.stop()
            self.app.pop_screen()
        elif key == "space":
            event.stop()
            self.app.open_leader()
        elif key == "question_mark":
            event.stop()
            self.app.push_screen(CheatsheetModal())

    def open_search(self) -> None:
        """Fuzzy-find a lesson by title and open it."""
        states = self.app.lesson_states()

        def label(lesson: Lesson) -> str:
            """Format one lesson for the finder list."""
            return f"{STATE_ICONS[states[lesson.id]]} D{lesson.domain} · {lesson.title}"

        def done(lesson: Lesson | None) -> None:
            """Open the chosen lesson."""
            if lesson is not None:
                self.open_lesson(lesson)

        self.app.push_screen(FuzzyModal(self.app.lessons, label), done)


class LessonScreen(Screen):
    """Scrollable lesson text, Enter starts the checkpoint exercises."""

    def __init__(self, lesson: Lesson) -> None:
        """Store the lesson to display."""
        super().__init__()
        self.lesson = lesson
        self.pending_g = False

    def compose(self) -> ComposeResult:
        """Build the markdown body and status bar."""
        with VerticalScroll(id="lesson-body"):
            yield Markdown(f"# {self.lesson.title}\n\n{self.lesson.body}")
        yield StatusBar()

    def on_mount(self) -> None:
        """Set the status bar."""
        n = len(self.lesson.exercises)
        self.query_one(StatusBar).set_status(
            f"lesson · D{self.lesson.domain}",
            self.lesson.title,
            f"{n} checkpoints",
            "Enter start checkpoints  j/k ctrl-d/u gg/G scroll  Esc back  ? help",
        )

    def on_key(self, event: events.Key) -> None:
        """Scroll the lesson or start its checkpoints."""
        scroll = self.query_one("#lesson-body", VerticalScroll)
        key = event.key
        if self.pending_g and key == "g":
            event.stop()
            self.pending_g = False
            scroll.scroll_to(y=0, animate=False)
            return
        self.pending_g = False
        if key == "enter":
            event.stop()
            self.app.start_lesson_quiz(self.lesson)
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
        elif key == "g":
            event.stop()
            self.pending_g = True
        elif key == "G":
            event.stop()
            scroll.scroll_to(y=scroll.max_scroll_y, animate=False)
        elif key == "escape":
            event.stop()
            self.app.pop_screen()
        elif key == "question_mark":
            event.stop()
            self.app.push_screen(CheatsheetModal())
