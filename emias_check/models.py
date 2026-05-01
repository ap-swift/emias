"""Модели данных для проверки медицинской документации.

Все основные dataclass-сущности собраны в одном месте,
чтобы избежать перекрёстных зависимостей между модулями.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


# ── PDF-извлечение ──────────────────────────────────────────────


@dataclass
class PageText:
    """Текст одной страницы PDF."""

    page_number: int
    text: str


@dataclass
class ExtractionResult:
    """Результат извлечения текста из PDF."""

    source_path: Path
    pages: list[PageText] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.pages)

    @property
    def num_pages(self) -> int:
        return len(self.pages)


# ── Разбор на разделы ───────────────────────────────────────────


@dataclass
class SectionContent:
    """Содержимое одного раздела истории болезни."""

    name: str
    text: str
    found: bool = True
    source_heading: str | None = None
    start_pos: int = 0
    page_hint: int | None = None


@dataclass
class ParseResult:
    """Результат разбиения текста на разделы."""

    sections: dict[str, SectionContent] = field(default_factory=dict)
    raw_text: str = ""

    @property
    def found_section_names(self) -> list[str]:
        return [name for name, sec in self.sections.items() if sec.found]


# ── Движок правил ──────────────────────────────────────────────


class Severity(str, Enum):
    """Уровень критичности замечания.

    - CRITICAL: грубые нарушения (отсутствие диагноза, ИДС, обязательных разделов)
    - MAJOR: существенные нарушения (нет МКБ-10, нет дат госпитализации)
    - MINOR: формальные замечания (нет рекомендаций, дозировок)
    - INFO: информационные замечания
    """

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"

    @property
    def label_ru(self) -> str:
        return {
            "critical": "Критическое",
            "major": "Существенное",
            "minor": "Формальное",
            "info": "Информационное",
        }[self.value]


@dataclass
class Finding:
    """Одно замечание, выявленное при проверке."""

    rule_id: str
    severity: Severity
    message: str
    source: str = ""
    section: str = ""
    details: str = ""
    evidence: str | None = None
    recommendation: str = ""
    manual_review: bool = False


@dataclass
class RuleResult:
    """Результат проверки одного правила."""

    rule_id: str
    rule_name: str
    passed: bool
    findings: list[Finding] = field(default_factory=list)


@dataclass
class CheckReport:
    """Сводный результат проверки документа по всем правилам."""

    results: list[RuleResult] = field(default_factory=list)

    @property
    def all_findings(self) -> list[Finding]:
        findings: list[Finding] = []
        for r in self.results:
            findings.extend(r.findings)
        return findings

    @property
    def criticals(self) -> list[Finding]:
        return [f for f in self.all_findings if f.severity == Severity.CRITICAL]

    @property
    def majors(self) -> list[Finding]:
        return [f for f in self.all_findings if f.severity == Severity.MAJOR]

    @property
    def minors(self) -> list[Finding]:
        return [f for f in self.all_findings if f.severity == Severity.MINOR]

    @property
    def infos(self) -> list[Finding]:
        return [f for f in self.all_findings if f.severity == Severity.INFO]

    @property
    def manual_reviews(self) -> list[Finding]:
        return [f for f in self.all_findings if f.manual_review]

    @property
    def total_rules(self) -> int:
        return len(self.results)

    @property
    def passed_rules(self) -> int:
        return sum(1 for r in self.results if r.passed)
