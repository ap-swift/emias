"""Тесты правил 530н на синтетических PDF-файлах."""

from __future__ import annotations

from pathlib import Path

import pytest

from emias_check.extractor import extract_text
from emias_check.models import (
    CheckReport,
    Finding,
    ParseResult,
    SectionContent,
    Severity,
)
from emias_check.parser import parse_sections
from emias_check.rules.base import run_all_rules

import emias_check.rules.order530n  # noqa: F401
import emias_check.rules.clinical  # noqa: F401

_SYNTHETIC_DIR = Path("/Users/dwuser/Downloads/medaudit_synthetic_histories")


def _check_pdf(filename: str) -> tuple[ParseResult, CheckReport]:
    path = _SYNTHETIC_DIR / filename
    if not path.exists():
        pytest.skip(f"Synthetic PDF not found: {path}")
    ext = extract_text(path)
    parsed = parse_sections(ext.full_text, [p.text for p in ext.pages])
    report = run_all_rules(parsed)
    return parsed, report


def _find_rule(report: CheckReport, rule_id: str) -> list[Finding]:
    for r in report.results:
        if r.rule_id == rule_id:
            return r.findings
    return []


def _has_violation(report: CheckReport, rule_id: str) -> bool:
    return len(_find_rule(report, rule_id)) > 0


def _make_parsed(**sections: str) -> ParseResult:
    """Create a ParseResult with given section names and text."""
    result = ParseResult(raw_text="\n".join(sections.values()))
    for name, text in sections.items():
        result.sections[name] = SectionContent(name=name, text=text)
    return result


# ═══════════════════════════════════════════════════════════════
# 1. Good case: all mandatory fields present, 0 criticals from 530n
# ═══════════════════════════════════════════════════════════════


class TestGoodCase:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.parsed, self.report = _check_pdf("01_good_i20_0_complete.pdf")

    def test_sections_found(self):
        names = list(self.parsed.sections.keys())
        assert "Паспортная часть" in names
        assert "Жалобы" in names
        assert "Объективный статус" in names
        assert "Эпикриз" in names

    def test_530n_001_required_sections_pass(self):
        assert not _has_violation(self.report, "530N-001")

    def test_530n_009_preliminary_diagnosis_pass(self):
        assert not _has_violation(self.report, "530N-009")

    def test_530n_010_justification_pass(self):
        assert not _has_violation(self.report, "530N-010")

    def test_530n_003_icd_pass(self):
        assert not _has_violation(self.report, "530N-003")

    def test_530n_019_allergy_pass(self):
        assert not _has_violation(self.report, "530N-019")

    def test_530n_023_hospitalization_justification_pass(self):
        assert not _has_violation(self.report, "530N-023")

    def test_530n_031_signatures_pass(self):
        assert not _has_violation(self.report, "530N-031")


# ═══════════════════════════════════════════════════════════════
# 2. No complaints
# ═══════════════════════════════════════════════════════════════


class TestNoComplaints:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.parsed, self.report = _check_pdf("02_no_complaints.pdf")

    def test_complaints_section_missing(self):
        assert "Жалобы" not in self.parsed.sections

    def test_530n_001_complaints_missing(self):
        findings = _find_rule(self.report, "530N-001")
        messages = [f.message for f in findings]
        assert any("Жалобы" in m for m in messages)

    def test_530n_016_complaints_not_empty_violation(self):
        assert _has_violation(self.report, "530N-016")


# ═══════════════════════════════════════════════════════════════
# 3. No diagnosis justification
# ═══════════════════════════════════════════════════════════════


class TestNoDiagnosisJustification:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.parsed, self.report = _check_pdf(
            "03_no_diagnosis_justification.pdf"
        )

    def test_justification_section_missing(self):
        assert "Обоснование предварительного диагноза" not in self.parsed.sections

    def test_530n_010_critical(self):
        findings = _find_rule(self.report, "530N-010")
        assert len(findings) > 0
        assert findings[0].severity == Severity.CRITICAL


# ═══════════════════════════════════════════════════════════════
# 4. No objective status (synthetic)
# ═══════════════════════════════════════════════════════════════


class TestNoObjectiveStatus:
    def test_missing_objective_status(self):
        parsed = _make_parsed(
            **{
                "Паспортная часть": "ФИО: Тест",
                "Диагноз": "I21.0 ОИМ",
            }
        )
        report = run_all_rules(parsed)
        assert _has_violation(report, "530N-001")
        findings_001 = _find_rule(report, "530N-001")
        assert any("Объективный статус" in f.message for f in findings_001)

    def test_short_objective_status(self):
        parsed = _make_parsed(
            **{
                "Объективный статус": "Объективный статус\nСостояние удовл.",
            }
        )
        report = run_all_rules(parsed)
        assert _has_violation(report, "530N-011")
        findings = _find_rule(report, "530N-011")
        assert findings[0].severity == Severity.MAJOR


# ═══════════════════════════════════════════════════════════════
# 5. No ICD code (synthetic)
# ═══════════════════════════════════════════════════════════════


class TestNoICD:
    def test_no_icd_code(self):
        parsed = _make_parsed(
            **{
                "Диагноз": "Диагноз\nОстрый инфаркт миокарда без кода",
            }
        )
        report = run_all_rules(parsed)
        assert _has_violation(report, "530N-003")
        findings = _find_rule(report, "530N-003")
        assert findings[0].severity == Severity.MAJOR

    def test_icd_present(self):
        parsed = _make_parsed(
            **{
                "Диагноз": "Диагноз\nI21.0 Острый инфаркт миокарда",
            }
        )
        report = run_all_rules(parsed)
        assert not _has_violation(report, "530N-003")


# ═══════════════════════════════════════════════════════════════
# 6. Short objective status (synthetic)
# ═══════════════════════════════════════════════════════════════


class TestShortObjectiveStatus:
    def test_exactly_at_threshold(self):
        text = "Объективный статус\n" + "x" * 100
        parsed = _make_parsed(**{"Объективный статус": text})
        report = run_all_rules(parsed)
        assert not _has_violation(report, "530N-011")

    def test_below_threshold(self):
        text = "Объективный статус\n" + "x" * 50
        parsed = _make_parsed(**{"Объективный статус": text})
        report = run_all_rules(parsed)
        assert _has_violation(report, "530N-011")


# ═══════════════════════════════════════════════════════════════
# 7. Discharge without epicrisis (synthetic)
# ═══════════════════════════════════════════════════════════════


class TestDischargeWithoutEpicrisis:
    def test_no_epicrisis_detected(self):
        parsed = _make_parsed(
            **{
                "Паспортная часть": "Пациент: Тест",
                "Диагноз": "I21.0",
            }
        )
        report = run_all_rules(parsed)
        assert _has_violation(report, "530N-001")
        findings = _find_rule(report, "530N-001")
        assert any("Эпикриз" in f.message for f in findings)


# ═══════════════════════════════════════════════════════════════
# 8. Manual review items
# ═══════════════════════════════════════════════════════════════


class TestManualReview:
    def test_manual_reviews_separated(self):
        parsed = _make_parsed(
            **{
                "Объективный статус": "Объективный статус\n" + "x" * 150,
            }
        )
        report = run_all_rules(parsed)
        manual = report.manual_reviews
        assert len(manual) > 0
        for f in manual:
            assert f.manual_review is True

    def test_530n_022_always_manual(self):
        parsed = _make_parsed(**{"Паспортная часть": "ФИО: Тест"})
        report = run_all_rules(parsed)
        findings = _find_rule(report, "530N-022")
        assert len(findings) == 1
        assert findings[0].manual_review is True


# ═══════════════════════════════════════════════════════════════
# 9. All findings have required fields
# ═══════════════════════════════════════════════════════════════


class TestFindingFields:
    @pytest.fixture(autouse=True)
    def setup(self):
        _, self.report = _check_pdf("01_good_i20_0_complete.pdf")

    def test_all_findings_have_rule_id(self):
        for f in self.report.all_findings:
            assert f.rule_id, f"Finding missing rule_id: {f}"

    def test_all_findings_have_severity(self):
        for f in self.report.all_findings:
            assert isinstance(f.severity, Severity)

    def test_all_findings_have_message(self):
        for f in self.report.all_findings:
            assert f.message, f"Finding missing message: {f}"

    def test_all_findings_have_source(self):
        for f in self.report.all_findings:
            assert f.source, f"Finding missing source: {f}"

    def test_all_findings_have_recommendation(self):
        for f in self.report.all_findings:
            assert f.recommendation, f"Finding missing recommendation: {f}"


# ═══════════════════════════════════════════════════════════════
# 10. Pneumonia complete case
# ═══════════════════════════════════════════════════════════════


class TestPneumoniaComplete:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.parsed, self.report = _check_pdf(
            "05_j18_9_pneumonia_complete.pdf"
        )

    def test_sections_detected(self):
        assert "Жалобы" in self.parsed.sections
        assert "Объективный статус" in self.parsed.sections

    def test_icd_found(self):
        assert not _has_violation(self.report, "530N-003")
