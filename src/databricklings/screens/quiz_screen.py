"""Quiz engine screens: practice and exam modes, results and answer review."""

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static

from databricklings.models import Domain
from databricklings.quiz import KIND_LABELS, QuizItem
from databricklings.scoring import is_fill_correct, score_exam
from databricklings.widgets import (
    ACCENT,
    DIM,
    FG,
    GREEN,
    RED,
    YELLOW,
    StatusBar,
    render_bar,
    render_code,
    render_options,
)
from databricklings.screens.overlays import CheatsheetModal, ConfirmModal

LETTER_KEYS = {chr(ord("a") + i): i for i in range(5)}
DIGIT_KEYS = {str(i + 1): i for i in range(5)}


class QuizScreen(Screen):
    """Run a list of QuizItems in practice (instant feedback) or exam (deferred) mode."""

    def __init__(
        self,
        items: list[QuizItem],
        mode: str = "practice",
        title: str = "quiz",
        duration_sec: int | None = None,
        on_answer=None,
        on_finish=None,
        requeue_wrong: bool = False,
    ) -> None:
        """Store quiz configuration and reset state."""
        super().__init__()
        self.items = list(items)
        self.mode = mode
        self.quiz_title = title
        self.duration_sec = duration_sec
        self.remaining = duration_sec or 0
        self.on_answer = on_answer
        self.on_finish = on_finish
        self.requeue_wrong = requeue_wrong
        self.index = 0
        self.cursor = 0
        self.selections: dict[str, set[int]] = {}
        self.fill_texts: dict[str, str] = {}
        self.marked: set[str] = set()
        self.first_results: dict[str, bool] = {}
        self.feedback: tuple[bool, str] | None = None
        self.pending_g = False
        self.finished = False

    def current(self) -> QuizItem:
        """Return the item under the cursor."""
        return self.items[self.index]

    def compose(self) -> ComposeResult:
        """Build the scrollable question layout plus status bar."""
        with VerticalScroll(id="quiz-scroll"):
            yield Static(id="q-header", classes="q-header")
            yield Static(id="q-stem", classes="q-stem")
            yield Static(id="q-code")
            yield Static(id="q-options", classes="q-options")
            yield Input(id="fill-input", placeholder="type answer, Enter to submit")
            yield Static(id="q-feedback")
        yield StatusBar()

    def on_mount(self) -> None:
        """Render the first question and start the exam timer if any."""
        if self.duration_sec:
            self.set_interval(1, self.tick)
        self.render_item()

    def tick(self) -> None:
        """Count down the exam timer and auto-finish at zero."""
        self.remaining -= 1
        if self.remaining <= 0 and not self.finished:
            self.finish()
            return
        self.update_status()

    def timer_label(self) -> str:
        """Format the remaining time as mm:ss."""
        if not self.duration_sec:
            return ""
        m, s = divmod(max(self.remaining, 0), 60)
        return f"⏱ {m:03d}:{s:02d}"

    def update_status(self) -> None:
        """Refresh the status bar for the current question."""
        item = self.current()
        mark = " ⚑" if item.id in self.marked else ""
        middle = f"Q {self.index + 1}/{len(self.items)}{mark}"
        if self.mode == "exam":
            answered = sum(1 for i in self.items if self.selections.get(i.id))
            middle += f"  answered {answered}/{len(self.items)}  marked {len(self.marked)}"
            hints = "j/k move  1-5/a-e pick  space mark/toggle  n/p next/prev  f finish  ? help"
        elif self.feedback is not None:
            hints = "Enter/n continue  ctrl-d/u scroll  ? help"
        else:
            hints = "j/k move  1-5/a-e pick  space toggle  Enter submit  Esc quit  ? help"
        self.query_one(StatusBar).set_status(self.quiz_title, middle, self.timer_label(), hints)

    def render_item(self) -> None:
        """Render stem, code, options and feedback for the current item."""
        item = self.current()
        header = Text()
        header.append(f"question {self.index + 1} of {len(self.items)}", style=DIM)
        header.append(f"  ·  {KIND_LABELS.get(item.kind, item.kind)}", style=DIM)
        if item.difficulty:
            header.append(f"  ·  {item.difficulty}", style=DIM)
        if item.id in self.marked:
            header.append("  ⚑ marked", style=YELLOW)
        self.query_one("#q-header", Static).update(header)
        stem = Text(item.stem.strip(), style=FG)
        if item.multi:
            stem.append("\n\n(select all that apply)", style=YELLOW)
        self.query_one("#q-stem", Static).update(stem)
        code_widget = self.query_one("#q-code", Static)
        if item.code:
            code_widget.update(render_code(item.code, item.code_lang))
            code_widget.display = True
        else:
            code_widget.display = False
        fill = self.query_one("#fill-input", Input)
        options = self.query_one("#q-options", Static)
        if item.fill:
            options.display = False
            fill.display = self.feedback is None
            if self.feedback is None:
                fill.value = self.fill_texts.get(item.id, "")
                fill.focus()
        else:
            fill.display = False
            options.display = True
            self.render_option_lines()
        self.render_feedback()
        self.update_status()
        self.query_one("#quiz-scroll", VerticalScroll).scroll_to(y=0, animate=False)

    def render_option_lines(self) -> None:
        """Redraw only the options block, with reveal colors when feedback is shown."""
        item = self.current()
        selected = self.selections.get(item.id, set())
        reveal = item.answer if self.feedback is not None else None
        self.query_one("#q-options", Static).update(
            render_options(item.options, self.cursor, selected, item.multi, reveal, selected)
        )

    def render_feedback(self) -> None:
        """Show or hide the feedback panel below the options."""
        panel = self.query_one("#q-feedback", Static)
        if self.feedback is None:
            panel.display = False
            panel.set_classes("")
            return
        ok, explanation = self.feedback
        text = Text()
        text.append("✓ correct\n\n" if ok else "✗ incorrect\n\n", style=f"bold {GREEN if ok else RED}")
        text.append(explanation.strip(), style=FG)
        text.append("\n\nEnter to continue", style=DIM)
        panel.update(text)
        panel.set_classes("q-feedback-ok" if ok else "q-feedback-bad")
        panel.display = True

    def selected_set(self) -> set[int]:
        """Return the mutable selection set for the current item."""
        return self.selections.setdefault(self.current().id, set())

    def pick(self, idx: int) -> None:
        """Select or toggle one option by index."""
        item = self.current()
        if self.feedback is not None or item.fill or idx >= len(item.options):
            return
        sel = self.selected_set()
        if item.multi:
            sel.symmetric_difference_update({idx})
        else:
            sel.clear()
            sel.add(idx)
        self.cursor = idx
        self.render_option_lines()
        self.update_status()

    def submit(self) -> None:
        """Grade the current item in practice mode and show feedback."""
        item = self.current()
        if item.fill:
            given = self.fill_texts.get(item.id, "")
            ok = is_fill_correct(item.answers, given)
        else:
            sel = self.selections.get(item.id, set())
            if not sel:
                return
            ok = sel == set(item.answer)
        first = item.id not in self.first_results
        if first:
            self.first_results[item.id] = ok
        if self.on_answer:
            self.on_answer(item, ok, first)
        explanation = item.explanation
        if item.fill and not ok:
            explanation = f"accepted answer: {item.answers[0]}\n\n{explanation}"
        self.feedback = (ok, explanation)
        if not ok and self.requeue_wrong:
            self.items.append(item)
        self.query_one("#fill-input", Input).display = False
        self.render_item()

    def advance(self) -> None:
        """Move past the feedback to the next item or finish the run."""
        item = self.current()
        self.feedback = None
        if not item.fill:
            self.selections.pop(item.id, None)
        self.fill_texts.pop(item.id, None)
        if self.index + 1 < len(self.items):
            self.index += 1
            self.cursor = 0
            self.render_item()
        else:
            self.finish()

    def goto(self, index: int) -> None:
        """Jump to another question in exam mode."""
        self.index = max(0, min(len(self.items) - 1, index))
        self.cursor = 0
        self.render_item()

    def finish(self) -> None:
        """Conclude the quiz and hand results to the finish callback."""
        if self.finished:
            return
        self.finished = True
        if self.mode == "exam":
            given = {qid: sorted(sel) for qid, sel in self.selections.items()}
            questions = [self.app.questions_by_id[i.id] for i in self.items]
            result = score_exam(questions, given)
            result["duration_sec"] = (self.duration_sec or 0) - max(self.remaining, 0)
            self.app.pop_screen()
            if self.on_finish:
                self.on_finish(result, self.items)
        else:
            correct = sum(1 for ok in self.first_results.values() if ok)
            self.app.pop_screen()
            if self.on_finish:
                self.on_finish(correct, len(self.first_results))

    def confirm_quit(self) -> None:
        """Ask before abandoning the run, then leave without saving."""
        def done(confirmed: bool | None) -> None:
            """Pop the quiz when the user confirms."""
            if confirmed:
                self.finished = True
                self.app.pop_screen()

        self.app.push_screen(ConfirmModal("Abandon this run? Nothing gets recorded."), done)

    def half_page(self, direction: int) -> None:
        """Scroll the question container by half a page."""
        scroll = self.query_one("#quiz-scroll", VerticalScroll)
        scroll.scroll_to(y=scroll.scroll_y + direction * scroll.size.height // 2, animate=False)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Submit a fill-in answer from the input."""
        event.stop()
        self.fill_texts[self.current().id] = event.value
        self.submit()

    def on_key(self, event: events.Key) -> None:
        """Handle vim-style quiz keys."""
        fill = self.query_one("#fill-input", Input)
        if fill.has_focus:
            if event.key == "escape":
                event.stop()
                self.set_focus(None)
            return
        key = event.key
        item = self.current()
        if self.pending_g and key == "g":
            event.stop()
            self.pending_g = False
            self.query_one("#quiz-scroll", VerticalScroll).scroll_to(y=0, animate=False)
            return
        self.pending_g = False
        if key == "question_mark":
            event.stop()
            self.app.push_screen(CheatsheetModal())
        elif key == "escape":
            event.stop()
            self.confirm_quit()
        elif key == "g":
            event.stop()
            self.pending_g = True
        elif key == "G":
            event.stop()
            scroll = self.query_one("#quiz-scroll", VerticalScroll)
            scroll.scroll_to(y=scroll.max_scroll_y, animate=False)
        elif key == "ctrl+d":
            event.stop()
            self.half_page(1)
        elif key == "ctrl+u":
            event.stop()
            self.half_page(-1)
        elif key == "j" and not item.fill and self.feedback is None:
            event.stop()
            self.cursor = min(len(item.options) - 1, self.cursor + 1)
            self.render_option_lines()
        elif key == "k" and not item.fill and self.feedback is None:
            event.stop()
            self.cursor = max(0, self.cursor - 1)
            self.render_option_lines()
        elif key in DIGIT_KEYS or key in LETTER_KEYS:
            event.stop()
            self.pick(DIGIT_KEYS.get(key, LETTER_KEYS.get(key)))
        elif key == "space":
            event.stop()
            if item.multi and self.feedback is None:
                sel = self.selected_set()
                sel.symmetric_difference_update({self.cursor})
                self.render_option_lines()
            elif self.mode == "exam":
                self.toggle_mark()
        elif key == "m" and self.mode == "exam":
            event.stop()
            self.toggle_mark()
        elif key == "enter":
            event.stop()
            if self.mode == "exam":
                self.goto(self.index + 1)
            elif self.feedback is not None:
                self.advance()
            else:
                self.submit()
        elif key in ("n", "right_square_bracket_q", "]"):
            event.stop()
            if self.mode == "exam":
                self.goto(self.index + 1)
            elif self.feedback is not None:
                self.advance()
        elif key in ("p", "["):
            event.stop()
            if self.mode == "exam":
                self.goto(self.index - 1)
        elif key == "f" and self.mode == "exam":
            event.stop()
            unanswered = len(self.items) - sum(1 for i in self.items if self.selections.get(i.id))
            msg = "Finish exam and grade it now?"
            if unanswered:
                msg = f"Finish exam? {unanswered} questions are unanswered and count as wrong."

            def done(confirmed: bool | None) -> None:
                """Finish the exam when confirmed."""
                if confirmed:
                    self.finish()

            self.app.push_screen(ConfirmModal(msg), done)

    def toggle_mark(self) -> None:
        """Toggle mark-for-review on the current question."""
        item = self.current()
        if item.id in self.marked:
            self.marked.discard(item.id)
        else:
            self.marked.add(item.id)
        self.render_item()


class ResultsScreen(Screen):
    """Exam results: score, pass hint, per-domain bars, entry to answer review."""

    def __init__(self, result: dict, items: list[QuizItem], domains: list[Domain]) -> None:
        """Store the graded result and the exam items."""
        super().__init__()
        self.result = result
        self.items = items
        self.domains = {d.id: d for d in domains}

    def compose(self) -> ComposeResult:
        """Build the results layout."""
        with VerticalScroll(id="quiz-scroll"):
            yield Static(id="results-body")
        yield StatusBar()

    def on_mount(self) -> None:
        """Render the result summary."""
        r = self.result
        pct = r["pct"]
        text = Text()
        text.append("exam results\n\n", style=f"bold {ACCENT}")
        color = GREEN if pct >= 80 else YELLOW if pct >= 65 else RED
        text.append(f"score: {r['score']}/{r['total']}  ({pct}%)\n", style=f"bold {color}")
        if pct >= 80:
            text.append("at or above the 80% target, you look ready\n", style=GREEN)
        else:
            text.append("aim for 80%+ on mocks before booking the real exam\n", style=DIM)
        mins = r.get("duration_sec", 0) // 60
        text.append(f"time used: {mins} min of 120\n\n", style=DIM)
        text.append("per domain\n", style=f"bold {ACCENT}")
        for did_str, stats in r["per_domain"].items():
            domain = self.domains.get(int(did_str))
            label = f"D{did_str} {domain.name if domain else ''}"
            pct_d = 100 * stats["correct"] / stats["total"] if stats["total"] else 0
            text.append("\n")
            text.append(render_bar(label, pct_d, count_label=f"{stats['correct']}/{stats['total']}"))
        self.query_one("#results-body", Static).update(text)
        self.query_one(StatusBar).set_status("results", "", "", "r review answers  Esc back  ? help")

    def on_key(self, event: events.Key) -> None:
        """Open the answer review or leave."""
        if event.key == "escape":
            event.stop()
            self.app.pop_screen()
        elif event.key == "r":
            event.stop()
            self.app.push_screen(AnswerReviewScreen(self.items, self.result))
        elif event.key == "question_mark":
            event.stop()
            self.app.push_screen(CheatsheetModal())


class AnswerReviewScreen(Screen):
    """Walk through every exam question with given answer, solution and explanation."""

    def __init__(self, items: list[QuizItem], result: dict) -> None:
        """Store items and the per-question answers from the result."""
        super().__init__()
        self.items = items
        self.answers = {a["qid"]: a for a in result["answers"]}
        self.index = 0
        self.pending_g = False

    def compose(self) -> ComposeResult:
        """Build the review layout."""
        with VerticalScroll(id="quiz-scroll"):
            yield Static(id="q-header", classes="q-header")
            yield Static(id="q-stem", classes="q-stem")
            yield Static(id="q-code")
            yield Static(id="q-options", classes="q-options")
            yield Static(id="q-feedback")
        yield StatusBar()

    def on_mount(self) -> None:
        """Render the first reviewed question."""
        self.render_item()

    def render_item(self) -> None:
        """Render one question with reveal colors and explanation."""
        item = self.items[self.index]
        answer = self.answers.get(item.id, {"given": [], "correct": False})
        ok = answer["correct"]
        header = Text()
        header.append(f"review {self.index + 1} of {len(self.items)}", style=DIM)
        header.append("  ✓ correct" if ok else "  ✗ wrong", style=GREEN if ok else RED)
        self.query_one("#q-header", Static).update(header)
        self.query_one("#q-stem", Static).update(Text(item.stem.strip(), style=FG))
        code_widget = self.query_one("#q-code", Static)
        if item.code:
            code_widget.update(render_code(item.code, item.code_lang))
            code_widget.display = True
        else:
            code_widget.display = False
        self.query_one("#q-options", Static).update(
            render_options(item.options, -1, set(answer["given"]), item.multi, item.answer, set(answer["given"]))
        )
        panel = self.query_one("#q-feedback", Static)
        text = Text(item.explanation.strip(), style=FG)
        panel.update(text)
        panel.set_classes("q-feedback-ok" if ok else "q-feedback-bad")
        panel.display = True
        self.query_one(StatusBar).set_status(
            "review answers", f"Q {self.index + 1}/{len(self.items)}", "", "n/p navigate  gg/G ctrl-d/u scroll  Esc back"
        )
        self.query_one("#quiz-scroll", VerticalScroll).scroll_to(y=0, animate=False)

    def on_key(self, event: events.Key) -> None:
        """Navigate reviewed questions with vim keys."""
        key = event.key
        scroll = self.query_one("#quiz-scroll", VerticalScroll)
        if self.pending_g and key == "g":
            event.stop()
            self.pending_g = False
            scroll.scroll_to(y=0, animate=False)
            return
        self.pending_g = False
        if key == "escape":
            event.stop()
            self.app.pop_screen()
        elif key in ("n", "j", "]"):
            event.stop()
            if self.index + 1 < len(self.items):
                self.index += 1
                self.render_item()
        elif key in ("p", "k", "["):
            event.stop()
            if self.index > 0:
                self.index -= 1
                self.render_item()
        elif key == "g":
            event.stop()
            self.pending_g = True
        elif key == "G":
            event.stop()
            scroll.scroll_to(y=scroll.max_scroll_y, animate=False)
        elif key == "ctrl+d":
            event.stop()
            scroll.scroll_to(y=scroll.scroll_y + scroll.size.height // 2, animate=False)
        elif key == "ctrl+u":
            event.stop()
            scroll.scroll_to(y=scroll.scroll_y - scroll.size.height // 2, animate=False)
        elif key == "question_mark":
            event.stop()
            self.app.push_screen(CheatsheetModal())
