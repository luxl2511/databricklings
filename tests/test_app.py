"""Headless TUI tests: boot, navigation, lesson flow, exam flow, persistence."""

from pathlib import Path

from databricklings.app import DatabricklingsApp
from databricklings.screens.dashboard import DashboardScreen
from databricklings.screens.learning import LearningPathScreen, LessonScreen
from databricklings.screens.quiz_screen import QuizScreen, ResultsScreen
from databricklings.screens.stats import DrillSetupScreen, StatsScreen


def make_app(content_dir: Path, tmp_path: Path) -> DatabricklingsApp:
    """Build an app instance against fixture content and a temp progress file."""
    return DatabricklingsApp(content_dir=content_dir, progress_path=tmp_path / "progress.json")


async def test_boot_shows_dashboard(content_dir, tmp_path):
    """App boots into the dashboard."""
    app = make_app(content_dir, tmp_path)
    async with app.run_test() as pilot:
        assert isinstance(app.screen, DashboardScreen)


async def test_navigate_screens(content_dir, tmp_path):
    """Direct keys reach learning path, stats, drill setup, and Esc backs out."""
    app = make_app(content_dir, tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("l")
        assert isinstance(app.screen, LearningPathScreen)
        await pilot.press("escape")
        await pilot.press("s")
        assert isinstance(app.screen, StatsScreen)
        await pilot.press("escape")
        await pilot.press("d")
        assert isinstance(app.screen, DrillSetupScreen)
        await pilot.press("escape")
        assert isinstance(app.screen, DashboardScreen)


async def test_leader_menu_opens_exam(content_dir, tmp_path):
    """Space leader plus e starts an exam, Esc plus confirm abandons it unrecorded."""
    app = make_app(content_dir, tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("space")
        await pilot.press("e")
        await pilot.pause()
        assert isinstance(app.screen, QuizScreen)
        await pilot.press("escape")
        await pilot.press("y")
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)
        assert app.progress.exams == []


async def test_lesson_flow_completes_and_persists(content_dir, tmp_path):
    """Answering all checkpoints correctly completes the lesson and unlocks the next."""
    app = make_app(content_dir, tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("l")
        await pilot.press("j")
        await pilot.press("enter")
        assert isinstance(app.screen, LessonScreen)
        await pilot.press("enter")
        assert isinstance(app.screen, QuizScreen)
        await pilot.press("a", "enter", "enter")
        await pilot.press("a", "b", "enter", "enter")
        for ch in "availableNow":
            await pilot.press(ch)
        await pilot.press("enter", "enter")
        await pilot.pause()
        first = app.lessons[0]
        assert app.progress.lessons[first.id]["completed_at"] is not None
        assert app.lesson_states()[app.lessons[1].id] in ("open", "partial")
    reloaded = make_app(content_dir, tmp_path)
    assert reloaded.progress.lessons[first.id]["completed_at"] is not None


async def test_drill_records_answers(content_dir, tmp_path):
    """A drill answer lands in the question history and Leitner queue."""
    app = make_app(content_dir, tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("d")
        await pilot.press("enter")
        assert isinstance(app.screen, QuizScreen)
        await pilot.press("b", "enter")
        await pilot.pause()
        wrong = [e for e in app.progress.questions.values() if e["history"]]
        assert wrong and wrong[0]["box"] == 1


async def test_exam_with_enough_questions(content_dir, tmp_path):
    """Exam starts with 59 questions when the pool is big enough, finishes and grades."""
    import yaml
    from tests.conftest import fixture_question

    questions = [fixture_question(1, 100 + n) for n in range(60)]
    (content_dir / "questions" / "extra.yaml").write_text(yaml.safe_dump({"questions": questions}))
    app = make_app(content_dir, tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("space")
        await pilot.press("e")
        await pilot.pause()
        assert isinstance(app.screen, QuizScreen)
        quiz = app.screen
        assert len(quiz.items) == 59
        assert quiz.remaining == 120 * 60
        await pilot.press("a")
        await pilot.press("space")
        assert quiz.items[0].id in quiz.marked
        await pilot.press("n")
        assert quiz.index == 1
        await pilot.press("p")
        assert quiz.index == 0
        await pilot.press("f")
        await pilot.press("y")
        await pilot.pause()
        assert isinstance(app.screen, ResultsScreen)
        assert len(app.progress.exams) == 1
        assert app.progress.exams[0]["total"] == 59
        await pilot.press("r")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.press("escape")
        assert isinstance(app.screen, DashboardScreen)


async def test_cheatsheet_overlay(content_dir, tmp_path):
    """Question mark opens and closes the cheatsheet."""
    app = make_app(content_dir, tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("question_mark")
        await pilot.pause()
        from databricklings.screens.overlays import CheatsheetModal

        assert isinstance(app.screen, CheatsheetModal)
        await pilot.press("escape")
        assert isinstance(app.screen, DashboardScreen)
