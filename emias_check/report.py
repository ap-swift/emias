"""Генерация отчётов (HTML, JSON) по результатам проверки."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from emias_check import __version__
from emias_check.models import CheckReport, ParseResult


def _get_templates_dir() -> Path:
    """Путь к шаблонам, работает и в обычном режиме, и в PyInstaller-сборке."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent
    return base / "emias_check" / "templates" if getattr(sys, "frozen", False) else base / "templates"


_TEMPLATES_DIR = _get_templates_dir()


def _report_context(
    check_report: CheckReport,
    parsed: ParseResult,
    source_name: str,
    num_pages: int,
) -> dict[str, Any]:
    """Общий контекст для отчёта (используется и HTML, и JSON)."""
    all_findings = check_report.all_findings
    violations = [f for f in all_findings if not f.manual_review]
    manual_reviews = check_report.manual_reviews

    return dict(
        source_name=source_name,
        num_pages=num_pages,
        generated_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
        passed_rules=check_report.passed_rules,
        total_rules=check_report.total_rules,
        num_criticals=len(check_report.criticals),
        num_majors=len(check_report.majors),
        num_minors=len(check_report.minors),
        num_infos=len(check_report.infos),
        num_manual_reviews=len(manual_reviews),
        criticals=[f for f in check_report.criticals if not f.manual_review],
        majors=[f for f in check_report.majors if not f.manual_review],
        minors=[f for f in check_report.minors if not f.manual_review],
        manual_reviews=manual_reviews,
        findings=all_findings,
        violations=violations,
        rule_results=check_report.results,
        sections=parsed.sections,
        version=__version__,
    )


def render_report(
    check_report: CheckReport,
    parsed: ParseResult,
    source_name: str,
    num_pages: int,
) -> str:
    """Сгенерировать HTML-отчёт."""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("report.html")
    ctx = _report_context(check_report, parsed, source_name, num_pages)
    return template.render(**ctx)


def render_json_report(
    check_report: CheckReport,
    parsed: ParseResult,
    source_name: str,
    num_pages: int,
) -> str:
    """Сгенерировать JSON-отчёт."""
    ctx = _report_context(check_report, parsed, source_name, num_pages)

    data: dict[str, Any] = {
        "version": ctx["version"],
        "generated_at": ctx["generated_at"],
        "source_name": ctx["source_name"],
        "num_pages": ctx["num_pages"],
        "summary": {
            "total_rules": ctx["total_rules"],
            "passed_rules": ctx["passed_rules"],
            "criticals": ctx["num_criticals"],
            "majors": ctx["num_majors"],
            "minors": ctx["num_minors"],
            "infos": ctx["num_infos"],
        },
        "findings": [
            {
                "rule_id": f.rule_id,
                "severity": f.severity.value,
                "source": f.source,
                "section": f.section,
                "message": f.message,
                "details": f.details,
                "evidence": f.evidence,
                "recommendation": f.recommendation,
                "manual_review": f.manual_review,
            }
            for f in ctx["findings"]
        ],
        "rules": [
            {
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "passed": r.passed,
                "findings_count": len(r.findings),
            }
            for r in ctx["rule_results"]
        ],
        "sections": {
            name: {
                "found": sec.found,
                "source_heading": sec.source_heading,
                "page": sec.page_hint,
                "text_length": len(sec.text),
                "text_preview": sec.text[:500],
            }
            for name, sec in ctx["sections"].items()
        },
    }

    return json.dumps(data, ensure_ascii=False, indent=2)


def save_report(content: str, output_path: Path) -> Path:
    """Сохранить отчёт (HTML или JSON) в файл."""
    output_path = Path(output_path)
    output_path.write_text(content, encoding="utf-8")
    return output_path
