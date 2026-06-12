"""Application entry point wiring content, progress and screens together."""

from textual.app import App

from databricklings import content, leitner, progress as progress_mod, sampling
from databricklings.models import Lesson
from databricklings.quiz import QuizItem, from_exercise, from_question
from databricklings.scoring import weak_subtopics
from databricklings.screens.dashboard import DashboardScreen
from databricklings.screens.learning import LearningPathScreen, LessonScreen
from databricklings.screens.overlays import WhichKeyModal
from databricklings.screens.quiz_screen import QuizScreen, ResultsScreen
from databricklings.screens.stats import DrillSetupScreen, StatsScreen


class DatabricklingsApp(App):
    """TUI study app for the Databricks Data Engineer Professional exam."""

    CSS_PATH = "theme.tcss"
    TITLE = "databricklings"

    def __init__(self, content_dir=None, progress_path=None) -> None:
        """Load content and progress, optionally from overridden paths for tests."""
        super().__init__()
        self.content_dir = content_dir or content.CONTENT_DIR
        self.progress_path = progress_path or progress_mod.PROGRESS_FILE
        self.domains = content.load_domains(self.content_dir)
        self.lessons = content.load_lessons(self.content_dir)
        self.questions = content.load_questions(self.content_dir)
        self.questions_by_id = {q.id: q for q in self.questions}
        self.progress = progress_mod.load_progress(self.progress_path)

    def on_mount(self) -> None:
        """Show the dashboard."""
        self.push_screen(DashboardScreen())

    def save(self) -> None:
        """Persist progress to disk."""
        progress_mod.save_progress(self.progress, self.progress_path)

    def lesson_states(self) -> dict[str, str]:
        """Compute done/partial/open/locked state for every lesson in curriculum order."""
        states = {}
        unlocked = True
        for lesson in self.lessons:
            entry = self.progress.lessons.get(lesson.id, {})
            if entry.get("completed_at"):
                states[lesson.id] = "done"
            elif unlocked:
                states[lesson.id] = "partial" if entry.get("passed") else "open"
                unlocked = False
            else:
                states[lesson.id] = "locked"
        return states

    def run_action_name(self, name: str) -> None:
        """Open a main screen by its leader action name."""
        if name == "learning":
            self.push_screen(LearningPathScreen())
        elif name == "exam":
            self.start_exam()
        elif name == "drill":
            self.push_screen(DrillSetupScreen())
        elif name == "review":
            self.start_review()
        elif name == "stats":
            self.push_screen(StatsScreen())
        elif name == "quit":
            self.exit()

    def open_leader(self) -> None:
        """Open the which-key leader menu."""
        def done(action: str | None) -> None:
            """Run the chosen leader action."""
            if action:
                self.run_action_name(action)

        self.push_screen(WhichKeyModal(), done)

    def record_quiz_answer(self, item: QuizItem, ok: bool, first: bool, mode: str) -> None:
        """Record one answered question into history and the Leitner queue."""
        if item.id in self.questions_by_id and first:
            progress_mod.record_answer(self.progress, item.id, ok, mode)
            leitner.schedule_after_answer(self.progress, item.id, ok)
            self.save()

    def start_lesson_quiz(self, lesson: Lesson) -> None:
        """Run the checkpoint exercises of a lesson, requeueing wrong answers."""
        items = [from_exercise(ex, lesson.domain) for ex in lesson.exercises]

        def on_answer(item: QuizItem, ok: bool, first: bool) -> None:
            """Mark the exercise as passed once answered correctly."""
            if ok:
                progress_mod.record_exercise_pass(self.progress, lesson.id, item.id)
                self.save()

        def on_finish(correct: int, total: int) -> None:
            """Complete the lesson when every checkpoint passed at least once."""
            passed = set(self.progress.lessons.get(lesson.id, {}).get("passed", []))
            if {ex.id for ex in lesson.exercises} <= passed:
                progress_mod.record_lesson_complete(self.progress, lesson.id)
                self.save()
                self.notify(f"lesson complete: {lesson.title}", timeout=3)
                if isinstance(self.screen, LessonScreen):
                    self.pop_screen()
            else:
                self.notify(f"{correct}/{total} on first try, wrong ones repeat next run", timeout=3)

        self.push_screen(
            QuizScreen(
                items,
                mode="practice",
                title=f"checkpoints · {lesson.title}",
                on_answer=on_answer,
                on_finish=on_finish,
                requeue_wrong=True,
            )
        )

    def start_exam(self) -> None:
        """Start a full 59 question, 120 minute mock exam."""
        if len(self.questions) < sampling.EXAM_SIZE:
            self.notify("not enough questions loaded for a full exam", severity="error", timeout=4)
            return
        picked = sampling.sample_exam(self.questions, self.domains)
        items = [from_question(q) for q in picked]

        def on_finish(result: dict, exam_items: list[QuizItem]) -> None:
            """Record the exam, update Leitner boxes and show results."""
            for answer in result["answers"]:
                progress_mod.record_answer(self.progress, answer["qid"], answer["correct"], "exam")
                leitner.schedule_after_answer(self.progress, answer["qid"], answer["correct"])
            result["started_at"] = progress_mod.now_iso()
            progress_mod.record_exam(self.progress, result)
            self.save()
            self.push_screen(ResultsScreen(result, exam_items, self.domains))

        self.push_screen(
            QuizScreen(
                items,
                mode="exam",
                title="mock exam",
                duration_sec=sampling.EXAM_MINUTES * 60,
                on_finish=on_finish,
            )
        )

    def start_drill(self, count: int, domain: int | None, weak: bool) -> None:
        """Start a quick drill, optionally filtered by domain or weak subtopics."""
        weak_set = weak_subtopics(self.progress, self.questions) if weak else None
        if weak and not weak_set:
            self.notify("no weak areas detected yet, drilling everything", timeout=3)
        picked = sampling.sample_drill(self.questions, count, domain, weak_set)
        if not picked:
            self.notify("no questions available for this filter", severity="error", timeout=3)
            return
        self.run_practice(picked, "quick drill", "drill")

    def start_review(self) -> None:
        """Run all due Leitner questions as a practice quiz."""
        due = leitner.due_question_ids(self.progress)
        picked = [self.questions_by_id[qid] for qid in due if qid in self.questions_by_id]
        if not picked:
            self.notify("review queue is empty, nothing due", timeout=3)
            return
        self.run_practice(picked, f"review due · {len(picked)}", "review")

    def run_practice(self, questions, title: str, mode: str) -> None:
        """Run questions in practice mode with recording and a summary toast."""
        items = [from_question(q) for q in questions]

        def on_answer(item: QuizItem, ok: bool, first: bool) -> None:
            """Record each first attempt."""
            self.record_quiz_answer(item, ok, first, mode)

        def on_finish(correct: int, total: int) -> None:
            """Show a short summary."""
            if total:
                self.notify(f"{title}: {correct}/{total} correct", timeout=4)

        self.push_screen(QuizScreen(items, mode="practice", title=title, on_answer=on_answer, on_finish=on_finish))


def main() -> None:
    """Run the databricklings app."""
    DatabricklingsApp().run()


if __name__ == "__main__":
    main()
