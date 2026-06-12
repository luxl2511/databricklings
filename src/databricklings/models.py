"""Dataclasses for domains, lessons, exercises and questions."""

from dataclasses import dataclass, field


CHOICE_TYPES = {"mcq", "multi", "predict_output", "spot_bug", "multiple_choice", "multi_select"}
MULTI_TYPES = {"multi", "multi_select"}


@dataclass(frozen=True)
class Domain:
    """One exam domain with its weight in percent."""

    id: int
    key: str
    name: str
    weight: int


@dataclass(frozen=True)
class Exercise:
    """One checkpoint exercise inside a lesson."""

    id: str
    type: str
    prompt: str
    options: list[str] = field(default_factory=list)
    answer: list[int] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)
    explanation: str = ""
    code: str = ""
    code_lang: str = "python"
    verify: bool = False

    def is_multi(self) -> bool:
        """Return whether more than one option must be selected."""
        return self.type in MULTI_TYPES or len(self.answer) > 1

    def is_fill_blank(self) -> bool:
        """Return whether the exercise expects typed text instead of a choice."""
        return self.type == "fill_blank"


@dataclass(frozen=True)
class Lesson:
    """One lesson with study text and checkpoint exercises."""

    id: str
    domain: int
    order: int
    title: str
    body: str
    exercises: list[Exercise]
    verify: bool = False


@dataclass(frozen=True)
class Question:
    """One exam question with options, answer indices and explanation."""

    id: str
    domain: int
    subtopic: str
    difficulty: str
    type: str
    stem: str
    options: list[str]
    answer: list[int]
    explanation: str
    code: str = ""
    code_lang: str = "python"
    verify: bool = False

    def is_multi(self) -> bool:
        """Return whether more than one option must be selected."""
        return self.type in MULTI_TYPES or len(self.answer) > 1
