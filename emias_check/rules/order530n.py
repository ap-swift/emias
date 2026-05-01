"""Правила проверки по приказу Минздрава России № 530н (приложение 4).

Каждое правило реализовано как отдельный класс, зарегистрированный
через декоратор @register_rule. Покрытие разделов A-Q чеклиста.
"""

from __future__ import annotations

import re
from datetime import datetime

from emias_check.concepts import has_concept
from emias_check.models import Finding, ParseResult, Severity
from emias_check.rules.base import Rule, register_rule

_SOURCE = "Приказ Минздрава России № 530н, приложение 4"

REQUIRED_SECTIONS = [
    "Паспортная часть",
    "Жалобы",
    "Анамнез заболевания",
    "Анамнез жизни",
    "Объективный статус",
    "Эпикриз",
]

_DIAGNOSIS_EQUIVALENTS = ("Диагноз", "Предварительный диагноз", "Клинический диагноз")
_TREATMENT_EQUIVALENTS = ("Лечение", "Назначения", "План лечения")

MIN_OBJECTIVE_STATUS_LEN = 100


def _snippet(text: str, max_len: int = 120) -> str:
    """Взять короткий фрагмент текста для evidence."""
    text = text.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _section_text(parsed: ParseResult, name: str) -> str:
    """Получить текст раздела или пустую строку."""
    sec = parsed.sections.get(name)
    return sec.text if sec else ""


def _section_content_len(parsed: ParseResult, name: str) -> int:
    """Длина содержимого раздела без заголовка."""
    sec = parsed.sections.get(name)
    if sec is None:
        return 0
    heading_len = len(sec.source_heading or "")
    return max(0, len(sec.text.strip()) - heading_len)


# ══════════════════════════════════════════════════════════════════
# A. ИДЕНТИФИКАЦИЯ ПАЦИЕНТА
# ══════════════════════════════════════════════════════════════════


# ── 530N-001: Обязательные разделы ──────────────────────────────


@register_rule
class RequiredSectionsRule(Rule):
    rule_id = "530N-001"
    rule_name = "Обязательные разделы"
    description = "Все обязательные разделы истории болезни должны присутствовать"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        findings: list[Finding] = []
        found = parsed.found_section_names
        for section_name in REQUIRED_SECTIONS:
            if section_name not in parsed.sections:
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=Severity.CRITICAL,
                        message=f"Отсутствует обязательный раздел: {section_name}",
                        section=section_name,
                        evidence=f"Найденные разделы: {', '.join(found) if found else 'нет'}",
                        recommendation=f"Добавить раздел «{section_name}» в историю болезни.",
                    )
                )
        if not any(eq in parsed.sections for eq in _DIAGNOSIS_EQUIVALENTS):
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.CRITICAL,
                    message="Отсутствует обязательный раздел: Диагноз",
                    section="Диагноз",
                    evidence=f"Найденные разделы: {', '.join(found) if found else 'нет'}",
                    recommendation="Добавить раздел «Диагноз» в историю болезни.",
                )
            )
        if not any(eq in parsed.sections for eq in _TREATMENT_EQUIVALENTS):
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.CRITICAL,
                    message="Отсутствует обязательный раздел: Лечение / Назначения",
                    section="Лечение",
                    evidence=f"Найденные разделы: {', '.join(found) if found else 'нет'}",
                    recommendation="Добавить раздел «Лечение» или «Назначения» в историю болезни.",
                )
            )
        return findings


# ── 530N-002: Паспортные данные ─────────────────────────────────

_FIO_PATTERN = re.compile(
    r"(?:ф\s*\.?\s*и\s*\.?\s*о\s*\.?|фамилия|пациент)\s*[:\-]?\s*[А-ЯЁ][а-яё]+",
    re.IGNORECASE,
)
_DOB_PATTERN = re.compile(
    r"(?:дата\s+рождения|д\s*\.?\s*р\s*\.?|род\.?)\s*[:\-]?\s*\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}",
    re.IGNORECASE,
)
_POLIS_PATTERN = re.compile(
    r"(?:полис|омс|страхов\w+)\s*[:\-№]?\s*\d{6,}",
    re.IGNORECASE,
)
_SEX_PATTERN = re.compile(
    r"(?:пол\s*[:\-]?\s*(?:мужской|женский|муж|жен)|мужчина|женщина)",
    re.IGNORECASE,
)


@register_rule
class PassportDataRule(Rule):
    rule_id = "530N-002"
    rule_name = "Паспортные данные"
    description = "Паспортная часть должна содержать ФИО, дату рождения, пол и номер полиса ОМС"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        findings: list[Finding] = []
        section = parsed.sections.get("Паспортная часть")
        if section is None:
            return []

        text = section.text

        if not _FIO_PATTERN.search(text):
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.CRITICAL,
                    message="Не найдены ФИО пациента в паспортной части",
                    section="Паспортная часть",
                    evidence=_snippet(text),
                    recommendation="Указать ФИО пациента в паспортной части.",
                )
            )
        if not _DOB_PATTERN.search(text):
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="Не найдена дата рождения пациента",
                    section="Паспортная часть",
                    evidence=_snippet(text),
                    recommendation="Указать дату рождения пациента.",
                )
            )
        if not _SEX_PATTERN.search(text):
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="Не указан пол пациента",
                    section="Паспортная часть",
                    evidence=_snippet(text),
                    recommendation="Указать пол пациента (мужской / женский).",
                )
            )
        if not _POLIS_PATTERN.search(text):
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="Не найден номер полиса ОМС",
                    section="Паспортная часть",
                    evidence=_snippet(text),
                    recommendation="Указать номер полиса ОМС пациента.",
                )
            )
        return findings


# ── 530N-003: Код МКБ-10 ───────────────────────────────────────

_ICD10_PATTERN = re.compile(r"[A-ZА-Я]\d{2}(?:\.\d{1,2})?")


@register_rule
class DiagnosisICD10Rule(Rule):
    rule_id = "530N-003"
    rule_name = "Код МКБ-10 в диагнозе"
    description = "Диагноз должен содержать код по МКБ-10"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        for sec_name in ("Диагноз", "Предварительный диагноз", "Клинический диагноз"):
            sec = parsed.sections.get(sec_name)
            if sec and _ICD10_PATTERN.search(sec.text):
                return []

        diag = parsed.sections.get("Диагноз")
        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.MAJOR,
                message="Не найден код МКБ-10 в разделе диагноза",
                section="Диагноз",
                details="Основной диагноз должен сопровождаться кодом по МКБ-10 "
                "(например, I21.0, J18.9)",
                evidence=_snippet(diag.text) if diag else None,
                recommendation="Указать код МКБ-10 рядом с диагнозом.",
            )
        ]


# ── 530N-004: Дневниковые записи ───────────────────────────────

_DIARY_DATE_PATTERN = re.compile(r"\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}")


@register_rule
class DiaryEntriesRule(Rule):
    rule_id = "530N-004"
    rule_name = "Дневниковые записи"
    description = "Дневниковые записи должны содержать дату осмотра и подпись врача"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        findings: list[Finding] = []
        section = parsed.sections.get("Дневники")
        if section is None:
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="Не найдены дневниковые записи",
                    section="Дневники",
                    recommendation="Добавить дневниковые записи врача с датами осмотров.",
                )
            )
            return findings

        text = section.text

        if not _DIARY_DATE_PATTERN.search(text):
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="В дневниковых записях не обнаружены даты осмотров",
                    section="Дневники",
                    evidence=_snippet(text),
                    recommendation="Указать даты осмотров в дневниковых записях.",
                )
            )
        if not has_concept("doctor_signature", text):
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="В дневниковых записях не найдены подписи (упоминания) врача",
                    section="Дневники",
                    evidence=_snippet(text),
                    recommendation="Указать ФИО и должность врача в каждой дневниковой записи.",
                )
            )
        return findings


# ── 530N-005: Рекомендации в эпикризе ──────────────────────────


@register_rule
class EpicrisisRecommendationsRule(Rule):
    rule_id = "530N-005"
    rule_name = "Рекомендации в эпикризе"
    description = "Выписной эпикриз должен содержать рекомендации пациенту"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        section = parsed.sections.get("Эпикриз")
        if section is None:
            return []

        if not has_concept("recommendation", section.text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="В эпикризе не найдены рекомендации",
                    section="Эпикриз",
                    evidence=_snippet(section.text),
                    recommendation="Добавить рекомендации по дальнейшему наблюдению и лечению.",
                )
            ]
        return []


# ── 530N-006: Информированное согласие ─────────────────────────


@register_rule
class InformedConsentRule(Rule):
    rule_id = "530N-006"
    rule_name = "Информированное согласие"
    description = "В документе должно быть упоминание информированного добровольного согласия"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        full_text = parsed.raw_text
        has_ids_section = "Информированное согласие" in parsed.sections

        if has_ids_section or has_concept("informed_consent", full_text):
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.CRITICAL,
                message="Не найдено упоминание информированного добровольного согласия (ИДС)",
                section="",
                details="Пациент должен подписать ИДС на госпитализацию и "
                "медицинские вмешательства",
                recommendation="Оформить и подписать ИДС на госпитализацию и медицинские вмешательства.",
            )
        ]


# ── 530N-007: Даты госпитализации ──────────────────────────────

_ADMISSION_DATE_PATTERN = re.compile(
    r"(?:дата\s+(?:поступления|госпитализации|приёма|приема))\s*[:\-]?\s*\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}",
    re.IGNORECASE,
)
_DISCHARGE_DATE_PATTERN = re.compile(
    r"(?:дата\s+(?:выписки|выбытия))\s*[:\-]?\s*\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}",
    re.IGNORECASE,
)
_DATE_EXTRACT_PATTERN = re.compile(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})")


@register_rule
class HospitalizationDatesRule(Rule):
    rule_id = "530N-007"
    rule_name = "Даты госпитализации"
    description = "Должны быть указаны дата госпитализации и дата выписки"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        findings: list[Finding] = []
        full_text = parsed.raw_text

        adm_section = parsed.sections.get("Дата и время поступления")
        has_adm = _ADMISSION_DATE_PATTERN.search(full_text) or (
            adm_section and _DATE_EXTRACT_PATTERN.search(adm_section.text)
        )

        if not has_adm:
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="Не найдена дата госпитализации (поступления)",
                    section="Паспортная часть",
                    evidence=_snippet(adm_section.text) if adm_section else None,
                    recommendation="Указать дату и время поступления пациента.",
                )
            )

        dis = _DISCHARGE_DATE_PATTERN.search(full_text)
        if not dis:
            epicrisis = parsed.sections.get("Эпикриз")
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="Не найдена дата выписки",
                    section="Эпикриз",
                    evidence=_snippet(epicrisis.text) if epicrisis else None,
                    recommendation="Указать дату выписки пациента.",
                )
            )
        return findings


# ── 530N-008: Дозировки в назначениях ──────────────────────────


@register_rule
class PrescriptionDetailsRule(Rule):
    rule_id = "530N-008"
    rule_name = "Дозировки в назначениях"
    description = "Лекарственные назначения должны содержать дозировки и кратность приёма"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        findings: list[Finding] = []
        text = ""
        for sec_name in ("Назначения", "Лечение"):
            sec = parsed.sections.get(sec_name)
            if sec:
                text = sec.text
                break
        if not text:
            return []

        if not has_concept("dosage", text):
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="В назначениях не найдены дозировки препаратов",
                    section="Назначения",
                    evidence=_snippet(text),
                    recommendation="Указать дозировки препаратов (например: 100 мг, 5 мл).",
                    manual_review=True,
                )
            )
        if not has_concept("frequency", text):
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="В назначениях не найдена кратность приёма",
                    section="Назначения",
                    evidence=_snippet(text),
                    recommendation="Указать кратность приёма (например: 2 раза в сутки).",
                    manual_review=True,
                )
            )
        return findings


# ══════════════════════════════════════════════════════════════════
# B. ДИАГНОЗЫ
# ══════════════════════════════════════════════════════════════════


# ── 530N-009: Предварительный диагноз ──────────────────────────

_PRELIMINARY_DIAG_PATTERN = re.compile(
    r"(?:предварительн\w+\s+диагноз|диагноз\s+(?:при\s+)?поступлени|диагноз\s+направивш)",
    re.IGNORECASE,
)


@register_rule
class PreliminaryDiagnosisRule(Rule):
    rule_id = "530N-009"
    rule_name = "Предварительный диагноз"
    description = "Должен быть указан предварительный диагноз при поступлении"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        if "Предварительный диагноз" in parsed.sections:
            return []
        if _PRELIMINARY_DIAG_PATTERN.search(parsed.raw_text):
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.CRITICAL,
                message="Не найден предварительный диагноз при поступлении",
                section="Диагноз",
                recommendation="Указать предварительный диагноз при поступлении.",
            )
        ]


# ── 530N-010: Обоснование предварительного диагноза ────────────

_JUSTIFICATION_SECTION = "Обоснование предварительного диагноза"


@register_rule
class DiagnosisJustificationRule(Rule):
    rule_id = "530N-010"
    rule_name = "Обоснование предварительного диагноза"
    description = "Должно быть представлено обоснование предварительного/клинического диагноза"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        sec = parsed.sections.get(_JUSTIFICATION_SECTION)
        if sec:
            content_len = _section_content_len(parsed, _JUSTIFICATION_SECTION)
            if content_len < 50:
                return [
                    Finding(
                        rule_id=self.rule_id,
                        severity=Severity.MAJOR,
                        message="Обоснование предварительного диагноза слишком краткое",
                        section=_JUSTIFICATION_SECTION,
                        evidence=_snippet(sec.text),
                        recommendation="Подробно описать, на основании каких данных установлен диагноз.",
                    )
                ]
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.CRITICAL,
                message="Не найден раздел «Обоснование предварительного диагноза»",
                section=_JUSTIFICATION_SECTION,
                recommendation="Добавить раздел «Обоснование предварительного диагноза» "
                "с описанием, на основании каких данных установлен диагноз.",
            )
        ]


# ── 530N-011: Объективный статус не пустой ─────────────────────


@register_rule
class ObjectiveStatusNotEmptyRule(Rule):
    rule_id = "530N-011"
    rule_name = "Полнота объективного статуса"
    description = "Раздел «Объективный статус» не должен быть пустым или слишком коротким"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        section = parsed.sections.get("Объективный статус")
        if section is None:
            return []

        content_len = _section_content_len(parsed, "Объективный статус")
        if content_len < MIN_OBJECTIVE_STATUS_LEN:
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="Раздел «Объективный статус» слишком краткий или пустой",
                    section="Объективный статус",
                    details=f"Содержимое раздела: {content_len} символов "
                    f"(минимум {MIN_OBJECTIVE_STATUS_LEN})",
                    evidence=_snippet(section.text),
                    recommendation="Подробно описать общее состояние, сознание, кожные покровы, "
                    "дыхательную и сердечно-сосудистую системы, живот.",
                )
            ]
        return []


# ── 530N-012: Подпись в эпикризе ───────────────────────────────


@register_rule
class EpicrisisSignatureRule(Rule):
    rule_id = "530N-012"
    rule_name = "Подпись в эпикризе"
    description = "Выписной эпикриз должен содержать подпись лечащего врача"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        section = parsed.sections.get("Эпикриз")
        if section is None:
            return []

        signatures = parsed.sections.get("Подписи")
        combined = section.text + " " + (signatures.text if signatures else "")

        if not has_concept("doctor_signature", combined):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="В эпикризе не найдена подпись (упоминание) лечащего врача",
                    section="Эпикриз",
                    evidence=_snippet(section.text),
                    recommendation="Указать ФИО и должность лечащего врача, подпись.",
                )
            ]
        return []


# ══════════════════════════════════════════════════════════════════
# НОВЫЕ ПРАВИЛА 530N-013 .. 530N-031 (чеклист A-Q)
# ══════════════════════════════════════════════════════════════════


# ── 530N-013: Номер карты / истории болезни (A) ────────────────

_CARD_NUMBER_PATTERN = re.compile(
    r"(?:номер\s+(?:карты|истории|ИБ)|№\s*(?:карты|ИБ|истории)|карта\s*№|TEST-\d+)",
    re.IGNORECASE,
)


@register_rule
class MedicalCardNumberRule(Rule):
    rule_id = "530N-013"
    rule_name = "Номер медицинской карты"
    description = "Должен быть указан номер медицинской карты / истории болезни"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        passport = _section_text(parsed, "Паспортная часть")
        full = parsed.raw_text[:1000]
        combined = passport + " " + full

        if _CARD_NUMBER_PATTERN.search(combined):
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.MINOR,
                message="Не найден номер медицинской карты / истории болезни",
                section="Паспортная часть",
                evidence=_snippet(passport) if passport else None,
                recommendation="Указать номер медицинской карты или истории болезни.",
            )
        ]


# ── 530N-014: Клинический диагноз (B) ─────────────────────────

_CLINICAL_DIAG_PATTERN = re.compile(
    r"(?:клинически\w+\s+диагноз|основной\s+диагноз|заключительн\w+\s+диагноз)",
    re.IGNORECASE,
)


@register_rule
class ClinicalDiagnosisRule(Rule):
    rule_id = "530N-014"
    rule_name = "Клинический диагноз"
    description = "Должен быть указан клинический (основной) диагноз"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        if "Клинический диагноз" in parsed.sections:
            return []
        if "Диагноз" in parsed.sections:
            diag_text = parsed.sections["Диагноз"].text
            if _CLINICAL_DIAG_PATTERN.search(diag_text) or _ICD10_PATTERN.search(diag_text):
                return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.MAJOR,
                message="Не найден клинический (основной) диагноз",
                section="Диагноз",
                recommendation="Указать клинический диагноз с кодом МКБ-10.",
                manual_review=True,
            )
        ]


# ── 530N-015: Диагноз при выписке (B) ─────────────────────────

_DISCHARGE_DIAG_PATTERN = re.compile(
    r"(?:диагноз|I\d{2}|J\d{2}|[A-Z]\d{2}\.\d)",
    re.IGNORECASE,
)


@register_rule
class DischargeDiagnosisRule(Rule):
    rule_id = "530N-015"
    rule_name = "Диагноз при выписке"
    description = "Выписной эпикриз должен содержать диагноз при выписке"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        epicrisis = parsed.sections.get("Эпикриз")
        if epicrisis is None:
            return []

        if _DISCHARGE_DIAG_PATTERN.search(epicrisis.text):
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.CRITICAL,
                message="В выписном эпикризе не найден диагноз при выписке",
                section="Эпикриз",
                evidence=_snippet(epicrisis.text),
                recommendation="Указать заключительный диагноз с кодом МКБ-10 в выписном эпикризе.",
            )
        ]


# ── 530N-016: Жалобы не пустые (C) ────────────────────────────


@register_rule
class ComplaintsNotEmptyRule(Rule):
    rule_id = "530N-016"
    rule_name = "Жалобы заполнены"
    description = "Раздел жалоб не должен быть пустым"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        sec = parsed.sections.get("Жалобы")
        if sec is None:
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="Отсутствуют жалобы пациента",
                    section="Жалобы",
                    recommendation="Добавить жалобы пациента при поступлении или указать, "
                    "что жалоб нет, с клиническим контекстом.",
                )
            ]

        content_len = _section_content_len(parsed, "Жалобы")
        if content_len < 20:
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="Раздел жалоб заполнен недостаточно подробно",
                    section="Жалобы",
                    details=f"Содержимое: {content_len} символов (минимум 20)",
                    evidence=_snippet(sec.text),
                    recommendation="Описать жалобы пациента подробнее.",
                )
            ]
        return []


# ── 530N-017: Анамнез заболевания не пуст (D) ──────────────────


@register_rule
class AnamnesisNotEmptyRule(Rule):
    rule_id = "530N-017"
    rule_name = "Анамнез заболевания заполнен"
    description = "Раздел анамнеза заболевания не должен быть пустым"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        sec = parsed.sections.get("Анамнез заболевания")
        if sec is None:
            return []

        content_len = _section_content_len(parsed, "Анамнез заболевания")
        if content_len < 30:
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="Анамнез заболевания заполнен недостаточно подробно",
                    section="Анамнез заболевания",
                    details=f"Содержимое: {content_len} символов (минимум 30)",
                    evidence=_snippet(sec.text),
                    recommendation="Описать анамнез заболевания подробнее.",
                )
            ]
        return []


# ── 530N-018: Анамнез жизни не пуст (E) ───────────────────────


@register_rule
class LifeAnamnesisNotEmptyRule(Rule):
    rule_id = "530N-018"
    rule_name = "Анамнез жизни заполнен"
    description = "Раздел анамнеза жизни не должен быть пустым"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        sec = parsed.sections.get("Анамнез жизни")
        if sec is None:
            return []

        content_len = _section_content_len(parsed, "Анамнез жизни")
        if content_len < 30:
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="Анамнез жизни заполнен недостаточно подробно",
                    section="Анамнез жизни",
                    details=f"Содержимое: {content_len} символов (минимум 30)",
                    evidence=_snippet(sec.text),
                    recommendation="Описать анамнез жизни подробнее.",
                )
            ]
        return []


# ── 530N-019: Аллергологический анамнез (F) ────────────────────

_ALLERGY_PATTERN = re.compile(
    r"(?:аллерг\w+\s+анамнез|аллергоанамнез|аллерги\w+\s+(?:отрицает|не\s+отягощ)"
    r"|лекарственн\w+\s+(?:аллерги|неперенос)"
    r"|аллергическ\w+\s+реакци|непереносимость)",
    re.IGNORECASE,
)


@register_rule
class AllergyAnamnesisRule(Rule):
    rule_id = "530N-019"
    rule_name = "Аллергологический анамнез"
    description = "Должен быть указан аллергологический анамнез"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        if "Аллергологический анамнез" in parsed.sections:
            return []
        if _ALLERGY_PATTERN.search(parsed.raw_text):
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.MAJOR,
                message="Не найден аллергологический анамнез",
                section="Аллергологический анамнез",
                recommendation="Указать аллергологический анамнез: наличие или отсутствие "
                "лекарственной аллергии и непереносимости.",
            )
        ]


# ── 530N-020: Описание систем органов в объективном статусе (G) ─

_VITAL_SYSTEMS = [
    ("дыхательная система / лёгкие", re.compile(
        r"(?:лёгк|легк|дыхан|ЧДД|хрип|везикулярн|аускультати)", re.IGNORECASE
    )),
    ("сердечно-сосудистая система", re.compile(
        r"(?:сердц|тоны\s+сердц|ЧСС|пульс|АД\s+\d|ритм)", re.IGNORECASE
    )),
    ("живот / органы пищеварения", re.compile(
        r"(?:живот|печен|селезён|селезен|пальпац\w+\s+(?:мягк|безболезн))", re.IGNORECASE
    )),
]


@register_rule
class VitalSystemsDescriptionRule(Rule):
    rule_id = "530N-020"
    rule_name = "Описание систем органов"
    description = "Объективный статус должен содержать описание жизненно важных систем"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        section = parsed.sections.get("Объективный статус")
        if section is None:
            return []

        findings: list[Finding] = []
        for system_name, pattern in _VITAL_SYSTEMS:
            if not pattern.search(section.text):
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        severity=Severity.INFO,
                        message=f"Не найдено описание: {system_name}",
                        section="Объективный статус",
                        evidence=_snippet(section.text),
                        recommendation=f"Добавить описание: {system_name}.",
                        manual_review=True,
                    )
                )
        return findings


# ── 530N-021: Первичный осмотр (H) ────────────────────────────

_PRIMARY_EXAM_PATTERN = re.compile(
    r"(?:первичн\w+\s+осмотр|осмотр\s+(?:врача\s+)?(?:приёмного|приемного)"
    r"|осмотр\s+при\s+поступлени|осмотр\s+лечащего\s+врач)",
    re.IGNORECASE,
)


@register_rule
class PrimaryExamRule(Rule):
    rule_id = "530N-021"
    rule_name = "Первичный осмотр врача"
    description = "Должен быть оформлен первичный осмотр врача"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        if "Первичный осмотр" in parsed.sections:
            return []
        has_obj = "Объективный статус" in parsed.sections
        has_complaints = "Жалобы" in parsed.sections
        has_diag = any(
            n in parsed.sections
            for n in ("Предварительный диагноз", "Диагноз")
        )
        if has_obj and has_complaints and has_diag:
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.INFO,
                message="Не найден явный раздел первичного осмотра врача",
                section="Первичный осмотр",
                recommendation="Оформить первичный осмотр с указанием жалоб, "
                "анамнеза, объективного статуса, предварительного диагноза и плана.",
                manual_review=True,
            )
        ]


# ── 530N-022: Полнота первичного осмотра (H) ──────────────────


@register_rule
class PrimaryExamCompletenessRule(Rule):
    rule_id = "530N-022"
    rule_name = "Полнота первичного осмотра"
    description = "Первичный осмотр должен содержать жалобы, анамнез, статус, диагноз, план"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.INFO,
                message="Полнота первичного осмотра требует ручной проверки",
                section="Первичный осмотр",
                details="Проверить наличие в первичном осмотре: жалоб, анамнеза, "
                "объективного статуса, предварительного диагноза, плана обследования "
                "и лечения",
                recommendation="Убедиться, что первичный осмотр содержит все необходимые компоненты.",
                manual_review=True,
            )
        ]


# ── 530N-023: Обоснование госпитализации (J) ──────────────────

_HOSPITALIZATION_JUSTIFICATION_PATTERN = re.compile(
    r"(?:обоснование\s+госпитализаци|показани\w+\s+к\s+госпитализац"
    r"|госпитализация\s+показана|нуждается\s+в\s+стационарн"
    r"|показано\s+лечение\s+в\s+условиях\s+стационар)",
    re.IGNORECASE,
)


@register_rule
class HospitalizationJustificationRule(Rule):
    rule_id = "530N-023"
    rule_name = "Обоснование госпитализации"
    description = "Должно быть указано обоснование госпитализации"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        if "Обоснование госпитализации" in parsed.sections:
            return []
        if _HOSPITALIZATION_JUSTIFICATION_PATTERN.search(parsed.raw_text):
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.MAJOR,
                message="Не найдено обоснование госпитализации",
                section="Обоснование госпитализации",
                recommendation="Добавить раздел «Обоснование госпитализации» "
                "или указать показания к стационарному лечению.",
            )
        ]


# ── 530N-024: План обследования не пуст (K) ───────────────────


@register_rule
class ExaminationPlanNotEmptyRule(Rule):
    rule_id = "530N-024"
    rule_name = "План обследования заполнен"
    description = "План обследования не должен быть пустым"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        sec = parsed.sections.get("План обследования")
        if sec is None:
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="Не найден план обследования",
                    section="План обследования",
                    recommendation="Добавить план обследования с перечнем назначенных исследований.",
                )
            ]

        content_len = _section_content_len(parsed, "План обследования")
        if content_len < 20:
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="План обследования заполнен недостаточно подробно",
                    section="План обследования",
                    details=f"Содержимое: {content_len} символов (минимум 20)",
                    evidence=_snippet(sec.text),
                    recommendation="Указать конкретные исследования в плане обследования.",
                )
            ]
        return []


# ── 530N-025: План лечения (L) ─────────────────────────────────


@register_rule
class TreatmentPlanRule(Rule):
    rule_id = "530N-025"
    rule_name = "План лечения"
    description = "Должен быть указан план лечения"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        for sec_name in ("План лечения", "Лечение", "Назначения"):
            if sec_name in parsed.sections:
                return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.MAJOR,
                message="Не найден план лечения",
                section="План лечения",
                recommendation="Добавить план лечения или лечебную тактику.",
            )
        ]


# ── 530N-026: Назначения не пусты (M) ─────────────────────────


@register_rule
class PrescriptionsNotEmptyRule(Rule):
    rule_id = "530N-026"
    rule_name = "Назначения заполнены"
    description = "Должны быть указаны медикаментозные назначения"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        for sec_name in ("Назначения", "Лечение"):
            sec = parsed.sections.get(sec_name)
            if sec:
                content_len = _section_content_len(parsed, sec_name)
                if content_len >= 30:
                    return []
                return [
                    Finding(
                        rule_id=self.rule_id,
                        severity=Severity.MAJOR,
                        message="Раздел назначений заполнен недостаточно подробно",
                        section=sec_name,
                        details=f"Содержимое: {content_len} символов (минимум 30)",
                        evidence=_snippet(sec.text),
                        recommendation="Указать препараты с дозировками и кратностью приёма.",
                    )
                ]

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.CRITICAL,
                message="Не найдены назначения",
                section="Назначения",
                recommendation="Добавить раздел назначений с указанием препаратов, "
                "дозировок, кратности и пути введения.",
            )
        ]


# ── 530N-027: Этапный эпикриз при длительной госпитализации (O)

_DATE_PATTERN = re.compile(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})")


def _parse_date(text: str) -> datetime | None:
    """Попробовать извлечь первую дату из текста."""
    m = _DATE_PATTERN.search(text)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        y += 2000
    try:
        return datetime(y, mo, d)
    except ValueError:
        return None


@register_rule
class IntermediateEpicrisisRule(Rule):
    rule_id = "530N-027"
    rule_name = "Этапный эпикриз"
    description = "При госпитализации > 10 дней должен быть этапный эпикриз"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        if "Этапный эпикриз" in parsed.sections:
            return []

        adm_text = _section_text(parsed, "Дата и время поступления")
        adm_date = _parse_date(adm_text) if adm_text else None
        if not adm_date:
            adm_match = _ADMISSION_DATE_PATTERN.search(parsed.raw_text)
            if adm_match:
                adm_date = _parse_date(adm_match.group())

        dis_match = _DISCHARGE_DATE_PATTERN.search(parsed.raw_text)
        dis_date = _parse_date(dis_match.group()) if dis_match else None

        if adm_date and dis_date:
            days = (dis_date - adm_date).days
            if days > 10:
                return [
                    Finding(
                        rule_id=self.rule_id,
                        severity=Severity.MAJOR,
                        message=f"Госпитализация {days} дней (> 10), но этапный эпикриз не найден",
                        section="Этапный эпикриз",
                        evidence=f"Поступление: {adm_date:%d.%m.%Y}, выписка: {dis_date:%d.%m.%Y}",
                        recommendation="Добавить этапный эпикриз при госпитализации более 10 дней.",
                    )
                ]
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.INFO,
                message="Не удалось определить длительность госпитализации для проверки "
                "необходимости этапного эпикриза",
                section="Этапный эпикриз",
                recommendation="Проверить наличие этапного эпикриза вручную, "
                "если госпитализация длилась более 10 дней.",
                manual_review=True,
            )
        ]


# ── 530N-028: Диагноз в выписном эпикризе (P) ─────────────────
# (covered by 530N-015 DischargeDiagnosisRule)


# ── 530N-029: Состояние при выписке (P) ────────────────────────

_DISCHARGE_STATE_PATTERN = re.compile(
    r"(?:состояни\w+\s+при\s+выписке|выпис\w+\s+(?:в|с)\s+(?:удовлетвор|улучшен|без\s+перемен)"
    r"|состояни\w+\s+(?:удовлетвор|стабильн|средн))",
    re.IGNORECASE,
)


@register_rule
class DischargeStateRule(Rule):
    rule_id = "530N-029"
    rule_name = "Состояние при выписке"
    description = "Выписной эпикриз должен содержать описание состояния при выписке"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        epicrisis = parsed.sections.get("Эпикриз")
        if epicrisis is None:
            return []

        if _DISCHARGE_STATE_PATTERN.search(epicrisis.text):
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.MAJOR,
                message="В выписном эпикризе не описано состояние при выписке",
                section="Эпикриз",
                evidence=_snippet(epicrisis.text),
                recommendation="Указать состояние пациента при выписке.",
            )
        ]


# ── 530N-030: Проведённое лечение в эпикризе (P) ──────────────

_TREATMENT_IN_EPICRISIS_PATTERN = re.compile(
    r"(?:проведен\w+\s+лечени|получал\w?\s+лечени|терапи|назначен\w+\s+терапи"
    r"|антиагрегантн|антикоагулянтн|антибактериальн)",
    re.IGNORECASE,
)


@register_rule
class TreatmentInEpicrisisRule(Rule):
    rule_id = "530N-030"
    rule_name = "Проведённое лечение в эпикризе"
    description = "Выписной эпикриз должен содержать сведения о проведённом лечении"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        epicrisis = parsed.sections.get("Эпикриз")
        if epicrisis is None:
            return []

        if _TREATMENT_IN_EPICRISIS_PATTERN.search(epicrisis.text):
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.MAJOR,
                message="В выписном эпикризе не описано проведённое лечение",
                section="Эпикриз",
                evidence=_snippet(epicrisis.text),
                recommendation="Указать проведённое лечение в выписном эпикризе.",
            )
        ]


# ── 530N-031: Глобальная проверка подписей (Q) ─────────────────


@register_rule
class GlobalSignaturesRule(Rule):
    rule_id = "530N-031"
    rule_name = "Подписи в документе"
    description = "Документ должен содержать подписи / упоминания врачей"
    source = _SOURCE

    def check(self, parsed: ParseResult) -> list[Finding]:
        has_signatures_section = "Подписи" in parsed.sections
        has_signature_mention = has_concept("doctor_signature", parsed.raw_text)

        if has_signatures_section or has_signature_mention:
            return []

        return [
            Finding(
                rule_id=self.rule_id,
                severity=Severity.MAJOR,
                message="В документе не найдены подписи / упоминания врачей",
                section="",
                recommendation="Указать ФИО и должность врача, подпись или отметку ЭП "
                "в ключевых разделах документа.",
            )
        ]
