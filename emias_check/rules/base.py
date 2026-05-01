"""Базовые классы движка правил проверки медицинской документации."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from emias_check.models import (
    CheckReport,
    Finding,
    RuleResult,
    Severity,
)

if TYPE_CHECKING:
    from emias_check.models import ParseResult

__all__ = [
    "CheckReport",
    "Finding",
    "Rule",
    "RuleResult",
    "Severity",
    "get_all_rules",
    "register_rule",
    "run_all_rules",
]


class Rule(ABC):
    """Абстрактное правило проверки."""

    rule_id: str = ""
    rule_name: str = ""
    description: str = ""
    source: str = ""

    @abstractmethod
    def check(self, parsed: ParseResult) -> list[Finding]:
        """Проверить документ и вернуть список замечаний.

        Пустой список означает, что правило пройдено успешно.
        """
        ...


_rule_registry: list[type[Rule]] = []


def register_rule(cls: type[Rule]) -> type[Rule]:
    """Декоратор для автоматической регистрации правила."""
    _rule_registry.append(cls)
    return cls


def get_all_rules() -> list[Rule]:
    """Вернуть экземпляры всех зарегистрированных правил."""
    return [cls() for cls in _rule_registry]


def run_all_rules(parsed: ParseResult) -> CheckReport:
    """Запустить все зарегистрированные правила и собрать отчёт."""
    report = CheckReport()
    for rule in get_all_rules():
        findings = rule.check(parsed)
        for f in findings:
            if not f.source and rule.source:
                f.source = rule.source
        result = RuleResult(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            passed=len(findings) == 0,
            findings=findings,
        )
        report.results.append(result)
    return report
