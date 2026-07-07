"""Typed dataclasses for karaoke documents."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Word:
    """A single timed word in a karaoke line."""

    text: str
    start: float
    end: float


@dataclass(frozen=True, slots=True)
class KaraokeLine:
    """A line of timed words."""

    words: tuple[Word, ...]
    start: float
    end: float


@dataclass(frozen=True, slots=True)
class KaraokeDocument:
    """A full karaoke transcript document."""

    lines: tuple[KaraokeLine, ...]
    source_format: str = "unknown"


@dataclass(frozen=True, slots=True)
class ValidationWarning:
    """A non-fatal validation issue."""

    code: str
    message: str
    path: str = ""


@dataclass
class ValidationReport:
    """Aggregated validation results."""

    warnings: list[ValidationWarning] = field(default_factory=list)
    errors: list[ValidationWarning] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def add_warning(self, code: str, message: str, path: str = "") -> None:
        self.warnings.append(ValidationWarning(code=code, message=message, path=path))

    def add_error(self, code: str, message: str, path: str = "") -> None:
        self.errors.append(ValidationWarning(code=code, message=message, path=path))
