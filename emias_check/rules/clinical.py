"""Правила проверки по клиническим рекомендациям (КР).

Реализованы проверки для соматических нозологий (I21, J18),
детской психиатрии — категория F (F84, F90, F80, F70–F79, F95) и
детской неврологии — категория G (G40, G80, G43, G71, G70, G12,
G24, G25, G91, G35).
"""

from __future__ import annotations

import re

from emias_check.concepts import has_concept
from emias_check.models import Finding, ParseResult, Severity
from emias_check.rules.base import Rule, register_rule

_ICD_I21 = re.compile(r"I21(?:\.\d)?")
_ICD_J18 = re.compile(r"J18(?:\.\d)?")

_ICD_F84 = re.compile(r"F84(?:\.\d)?")
_ICD_F90 = re.compile(r"F90(?:\.\d)?")
_ICD_F80 = re.compile(r"F8[0-3](?:\.\d)?")
_ICD_F7X = re.compile(r"F7\d(?:\.\d)?")
_ICD_F95 = re.compile(r"F95(?:\.\d)?")

_ICD_G40 = re.compile(r"G40(?:\.\d)?")
_ICD_G80 = re.compile(r"G80(?:\.\d)?")
_ICD_G43 = re.compile(r"G43(?:\.\d)?")
_ICD_G71 = re.compile(r"G71(?:\.\d)?")
_ICD_G70 = re.compile(r"G70(?:\.\d)?")
_ICD_G12 = re.compile(r"G12(?:\.\d)?")
_ICD_G24 = re.compile(r"G24(?:\.\d)?")
_ICD_G25 = re.compile(r"G25(?:\.\d)?")
_ICD_G91 = re.compile(r"G91(?:\.\d)?")
_ICD_G35 = re.compile(r"G35\b")


def _snippet(text: str, max_len: int = 120) -> str:
    text = text.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


@register_rule
class AcuteMyocardialInfarctionRule(Rule):
    rule_id = "КР-001"
    rule_name = "Антиагреганты при ОИМ"
    description = (
        "При остром инфаркте миокарда (I21) в лечении должен быть назначен "
        "аспирин или другой антиагрегант"
    )
    source = "КР «Острый инфаркт миокарда», 2024"

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_I21.search(diagnosis.text):
            return []

        treatment = parsed.sections.get("Лечение")
        treatment_text = treatment.text if treatment else ""
        epicrisis = parsed.sections.get("Эпикриз")
        epicrisis_text = epicrisis.text if epicrisis else ""
        combined = treatment_text + " " + epicrisis_text

        if not has_concept("aspirin", combined):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При ОИМ (I21) не найдено назначение аспирина / антиагреганта",
                    section="Лечение",
                    details="Согласно клиническим рекомендациям, при остром "
                    "инфаркте миокарда показано назначение антиагрегантной "
                    "терапии (ацетилсалициловая кислота)",
                    evidence=_snippet(combined),
                )
            ]
        return []


@register_rule
class PneumoniaAntibioticsRule(Rule):
    rule_id = "КР-002"
    rule_name = "Антибиотики при пневмонии"
    description = (
        "При внебольничной пневмонии (J18) в лечении должны быть назначены "
        "антибактериальные препараты"
    )
    source = "КР «Внебольничная пневмония», 2024"

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_J18.search(diagnosis.text):
            return []

        treatment = parsed.sections.get("Лечение")
        treatment_text = treatment.text if treatment else ""
        epicrisis = parsed.sections.get("Эпикриз")
        epicrisis_text = epicrisis.text if epicrisis else ""
        combined = treatment_text + " " + epicrisis_text

        if not has_concept("antibiotic", combined):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При пневмонии (J18) не найдено назначение антибиотиков",
                    section="Лечение",
                    details="Согласно клиническим рекомендациям, при внебольничной "
                    "пневмонии показана антибактериальная терапия",
                    evidence=_snippet(combined),
                )
            ]
        return []


# ── Категория F (дети) ─────────────────────────────────────────

_SRC_F84 = "КР «Расстройства аутистического спектра» (ID 594), 2024"
_SRC_F90 = "КР «Гиперкинетические расстройства», 2024"
_SRC_F80 = "КР «Специфические расстройства развития речи у детей», 2024"
_SRC_F7X = "КР «Умственная отсталость у детей», 2024"
_SRC_F95 = "КР «Тикозные расстройства», 2024"


# ── КР-003: Консультация психиатра при РАС ────────────────────


@register_rule
class ASDPsychiatristRule(Rule):
    rule_id = "КР-003"
    rule_name = "Консультация психиатра при РАС"
    description = (
        "При расстройствах аутистического спектра (F84) "
        "обязательна консультация врача-психиатра"
    )
    source = _SRC_F84

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_F84.search(diagnosis.text):
            return []

        if not has_concept("psychiatrist_consult", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При РАС (F84) не найдено упоминание консультации психиатра",
                    section="Диагноз",
                    details="Согласно КР, диагностика и ведение РАС требуют "
                    "обязательного участия врача-психиатра",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-004: Генетическое обследование при РАС ─────────────────


@register_rule
class ASDGeneticTestingRule(Rule):
    rule_id = "КР-004"
    rule_name = "Генетическое обследование при РАС"
    description = (
        "При расстройствах аутистического спектра (F84) "
        "рекомендовано генетическое обследование для уточнения этиологии"
    )
    source = _SRC_F84

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_F84.search(diagnosis.text):
            return []

        if not has_concept("genetic_testing", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При РАС (F84) не найдено упоминание генетического обследования",
                    section="Диагноз",
                    details="Согласно КР, всем детям с установленным диагнозом РАС "
                    "рекомендовано генетическое обследование (хромосомный "
                    "микроматричный анализ, кариотипирование и др.)",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-005: ЭЭГ при СДВГ ─────────────────────────────────────


@register_rule
class ADHDEEGRule(Rule):
    rule_id = "КР-005"
    rule_name = "ЭЭГ при СДВГ"
    description = (
        "При гиперкинетическом расстройстве / СДВГ (F90) "
        "рекомендовано проведение ЭЭГ для дифференциальной диагностики"
    )
    source = _SRC_F90

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_F90.search(diagnosis.text):
            return []

        if not has_concept("eeg", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При СДВГ (F90) не найдено упоминание ЭЭГ",
                    section="Диагноз",
                    details="Согласно КР, при СДВГ рекомендовано проведение ЭЭГ "
                    "для исключения органических поражений ЦНС и эпилептиформной "
                    "активности",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-006: Консультация психолога при СДВГ ───────────────────


@register_rule
class ADHDPsychologistRule(Rule):
    rule_id = "КР-006"
    rule_name = "Консультация психолога при СДВГ"
    description = (
        "При СДВГ (F90) рекомендована консультация психолога "
        "для нейропсихологической диагностики"
    )
    source = _SRC_F90

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_F90.search(diagnosis.text):
            return []

        if not has_concept("psychologist_consult", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При СДВГ (F90) не найдено упоминание консультации психолога",
                    section="Диагноз",
                    details="Согласно КР, при СДВГ рекомендована консультация "
                    "психолога / нейропсихолога для оценки когнитивных функций",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-007: Логопедическое обследование при F80 ───────────────


@register_rule
class SpeechDisorderSpeechTherapistRule(Rule):
    rule_id = "КР-007"
    rule_name = "Логопедическое обследование при расстройствах речи"
    description = (
        "При специфических расстройствах развития речи (F80) "
        "обязательна консультация логопеда"
    )
    source = _SRC_F80

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_F80.search(diagnosis.text):
            return []

        if not has_concept("speech_therapist", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При расстройстве речи (F80) не найдено упоминание "
                    "логопедического обследования",
                    section="Диагноз",
                    details="Согласно КР, при специфических расстройствах развития "
                    "речи обязательна консультация логопеда / дефектолога",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-008: Аудиометрия при F80 ───────────────────────────────


@register_rule
class SpeechDisorderAudiometryRule(Rule):
    rule_id = "КР-008"
    rule_name = "Аудиометрия при расстройствах речи"
    description = (
        "При специфических расстройствах развития речи (F80) "
        "рекомендована аудиометрия для исключения нарушений слуха"
    )
    source = _SRC_F80

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_F80.search(diagnosis.text):
            return []

        if not has_concept("audiometry", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При расстройстве речи (F80) не найдено упоминание "
                    "аудиометрии",
                    section="Диагноз",
                    details="Согласно КР, при расстройствах развития речи "
                    "рекомендована пороговая тональная аудиометрия для "
                    "исключения нарушений слуха",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-009: ЭЭГ при умственной отсталости ─────────────────────


@register_rule
class IntellectualDisabilityEEGRule(Rule):
    rule_id = "КР-009"
    rule_name = "ЭЭГ при умственной отсталости"
    description = (
        "При умственной отсталости (F70–F79) рекомендовано "
        "проведение ЭЭГ хотя бы однократно"
    )
    source = _SRC_F7X

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_F7X.search(diagnosis.text):
            return []

        if not has_concept("eeg", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При умственной отсталости (F7x) не найдено "
                    "упоминание ЭЭГ",
                    section="Диагноз",
                    details="Согласно КР, при умственной отсталости рекомендовано "
                    "проведение ЭЭГ хотя бы однократно для выявления "
                    "эпилептиформной активности",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-010: Генетическое обследование при F7x ─────────────────


@register_rule
class IntellectualDisabilityGeneticRule(Rule):
    rule_id = "КР-010"
    rule_name = "Генетическое обследование при умственной отсталости"
    description = (
        "При умственной отсталости (F70–F79) рекомендовано "
        "цитогенетическое / генетическое исследование"
    )
    source = _SRC_F7X

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_F7X.search(diagnosis.text):
            return []

        if not has_concept("genetic_testing", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При умственной отсталости (F7x) не найдено "
                    "упоминание генетического обследования",
                    section="Диагноз",
                    details="Согласно КР, при умственной отсталости рекомендовано "
                    "цитогенетическое исследование (кариотипирование) хотя бы "
                    "однократно для уточнения этиологии",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-011: Консультация невролога при тиках ──────────────────


@register_rule
class TicDisorderNeurologistRule(Rule):
    rule_id = "КР-011"
    rule_name = "Консультация невролога при тиках"
    description = (
        "При тикозных расстройствах (F95) рекомендована "
        "консультация невролога"
    )
    source = _SRC_F95

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_F95.search(diagnosis.text):
            return []

        if not has_concept("neurologist_consult", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При тикозном расстройстве (F95) не найдено "
                    "упоминание консультации невролога",
                    section="Диагноз",
                    details="Согласно КР, при тикозных расстройствах рекомендован "
                    "осмотр невролога для дифференциальной диагностики "
                    "и исключения органической патологии",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-012: Оценка коморбидных расстройств при тиках ──────────


@register_rule
class TicDisorderComorbidityRule(Rule):
    rule_id = "КР-012"
    rule_name = "Оценка коморбидных расстройств при тиках"
    description = (
        "При тикозных расстройствах (F95) необходима оценка "
        "сопутствующих состояний (СДВГ, ОКР, тревожность)"
    )
    source = _SRC_F95

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_F95.search(diagnosis.text):
            return []

        if not has_concept("comorbidity_assessment", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При тикозном расстройстве (F95) не найдена "
                    "оценка коморбидных состояний",
                    section="Диагноз",
                    details="Согласно КР, при тикозных расстройствах / синдроме "
                    "Туретта необходима оценка сопутствующих расстройств "
                    "(СДВГ, ОКР, тревожность)",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── Категория G (дети) ─────────────────────────────────────────

_SRC_G40 = "КР «Эпилепсия и эпилептический статус у взрослых и детей» (ID 741), 2022"
_SRC_G80 = "КР «Детский церебральный паралич у детей», 2024"
_SRC_G43 = "КР «Мигрень у детей», 2024"
_SRC_G71 = "КР «Прогрессирующая мышечная дистрофия Дюшенна/Беккера», 2023"
_SRC_G70 = "КР «Миастения», 2024"
_SRC_G12 = "КР «Проксимальная спинальная мышечная атрофия 5q», 2024"
_SRC_G24 = "КР «Дистония», 2024"
_SRC_G25 = "КР «Экстрапирамидные расстройства», 2024"
_SRC_G91 = "КР «Гидроцефалия», 2024"
_SRC_G35 = "КР «Рассеянный склероз», 2025"


# ── КР-013: ЭЭГ при эпилепсии ─────────────────────────────────


@register_rule
class EpilepsyEEGRule(Rule):
    rule_id = "КР-013"
    rule_name = "ЭЭГ при эпилепсии"
    description = (
        "При эпилепсии (G40) обязательно проведение ЭЭГ "
        "как основного метода диагностики"
    )
    source = _SRC_G40

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G40.search(diagnosis.text):
            return []

        if not has_concept("eeg", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При эпилепсии (G40) не найдено упоминание ЭЭГ",
                    section="Диагноз",
                    details="Согласно КР, ЭЭГ является основным методом "
                    "диагностики эпилепсии; при отсутствии разрядов на "
                    "рутинной ЭЭГ показан видео-ЭЭГ-мониторинг",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-014: Противоэпилептические препараты при эпилепсии ─────


@register_rule
class EpilepsyAnticonvulsantRule(Rule):
    rule_id = "КР-014"
    rule_name = "Противоэпилептические препараты при эпилепсии"
    description = (
        "При эпилепсии (G40) в лечении должны быть назначены "
        "противоэпилептические препараты"
    )
    source = _SRC_G40

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G40.search(diagnosis.text):
            return []

        treatment = parsed.sections.get("Лечение")
        treatment_text = treatment.text if treatment else ""
        epicrisis = parsed.sections.get("Эпикриз")
        epicrisis_text = epicrisis.text if epicrisis else ""
        combined = treatment_text + " " + epicrisis_text

        if not has_concept("anticonvulsant", combined):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При эпилепсии (G40) не найдено назначение "
                    "противоэпилептических препаратов",
                    section="Лечение",
                    details="Согласно КР, при эпилепсии показана терапия "
                    "антиконвульсантами (вальпроевая кислота, карбамазепин, "
                    "ламотриджин, леветирацетам и др.)",
                    evidence=_snippet(combined),
                )
            ]
        return []


# ── КР-015: МРТ при ДЦП ───────────────────────────────────────


@register_rule
class CerebralPalsyMRIRule(Rule):
    rule_id = "КР-015"
    rule_name = "МРТ головного мозга при ДЦП"
    description = (
        "При детском церебральном параличе (G80) обязательно "
        "проведение МРТ головного мозга"
    )
    source = _SRC_G80

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G80.search(diagnosis.text):
            return []

        if not has_concept("mri", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При ДЦП (G80) не найдено упоминание МРТ "
                    "головного мозга",
                    section="Диагноз",
                    details="Согласно КР, МРТ головного мозга обязательно "
                    "для исключения структурных аномалий и дифференциальной "
                    "диагностики",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-016: Реабилитация при ДЦП ──────────────────────────────


@register_rule
class CerebralPalsyRehabRule(Rule):
    rule_id = "КР-016"
    rule_name = "Реабилитация при ДЦП"
    description = (
        "При детском церебральном параличе (G80) должна быть "
        "назначена реабилитация (ЛФК, физиотерапия, кинезотерапия)"
    )
    source = _SRC_G80

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G80.search(diagnosis.text):
            return []

        if not has_concept("rehabilitation", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При ДЦП (G80) не найдено упоминание реабилитации",
                    section="Лечение",
                    details="Согласно КР, при ДЦП обязательна физическая "
                    "реабилитация (ЛФК, массаж, кинезотерапия, "
                    "механотерапия)",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-017: Консультация невролога при мигрени ─────────────────


@register_rule
class MigraineNeurologistRule(Rule):
    rule_id = "КР-017"
    rule_name = "Консультация невролога при мигрени"
    description = (
        "При мигрени (G43) рекомендована консультация невролога"
    )
    source = _SRC_G43

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G43.search(diagnosis.text):
            return []

        if not has_concept("neurologist_consult", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При мигрени (G43) не найдено упоминание "
                    "консультации невролога",
                    section="Диагноз",
                    details="Согласно КР, диагностика и ведение мигрени "
                    "у детей требуют участия невролога",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-018: Обезболивание при мигрени ──────────────────────────


@register_rule
class MigrainePainReliefRule(Rule):
    rule_id = "КР-018"
    rule_name = "Обезболивание при мигрени"
    description = (
        "При мигрени (G43) в лечении должны быть назначены "
        "НПВП и/или триптаны для купирования приступов"
    )
    source = _SRC_G43

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G43.search(diagnosis.text):
            return []

        treatment = parsed.sections.get("Лечение")
        treatment_text = treatment.text if treatment else ""
        epicrisis = parsed.sections.get("Эпикриз")
        epicrisis_text = epicrisis.text if epicrisis else ""
        combined = treatment_text + " " + epicrisis_text

        if not (has_concept("nsaid", combined) or has_concept("triptan", combined)):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При мигрени (G43) не найдено назначение "
                    "обезболивающих (НПВП / триптаны)",
                    section="Лечение",
                    details="Согласно КР, для купирования приступов мигрени "
                    "у детей показаны НПВП (ибупрофен) и/или триптаны",
                    evidence=_snippet(combined),
                )
            ]
        return []


# ── КР-019: КФК при миопатии ──────────────────────────────────


@register_rule
class MyopathyCKRule(Rule):
    rule_id = "КР-019"
    rule_name = "КФК при миопатии"
    description = (
        "При миопатии / мышечной дистрофии (G71) обязательно "
        "определение уровня КФК"
    )
    source = _SRC_G71

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G71.search(diagnosis.text):
            return []

        if not has_concept("creatine_kinase", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При миопатии (G71) не найдено упоминание "
                    "определения КФК",
                    section="Диагноз",
                    details="Согласно КР, определение уровня КФК "
                    "(креатинфосфокиназы) является ключевым маркером "
                    "при мышечных дистрофиях",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-020: Генетическое обследование при миопатии ─────────────


@register_rule
class MyopathyGeneticRule(Rule):
    rule_id = "КР-020"
    rule_name = "Генетическое обследование при миопатии"
    description = (
        "При миопатии / мышечной дистрофии (G71) рекомендовано "
        "молекулярно-генетическое исследование"
    )
    source = _SRC_G71

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G71.search(diagnosis.text):
            return []

        if not has_concept("genetic_testing", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При миопатии (G71) не найдено упоминание "
                    "генетического обследования",
                    section="Диагноз",
                    details="Согласно КР, при мышечных дистрофиях "
                    "рекомендовано молекулярно-генетическое исследование "
                    "для подтверждения диагноза",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-021: ЭМГ при миастении ─────────────────────────────────


@register_rule
class MyastheniaEMGRule(Rule):
    rule_id = "КР-021"
    rule_name = "ЭМГ при миастении"
    description = (
        "При миастении (G70) рекомендовано проведение ЭМГ "
        "(ритмическая стимуляция нерва)"
    )
    source = _SRC_G70

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G70.search(diagnosis.text):
            return []

        if not has_concept("emg", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При миастении (G70) не найдено упоминание ЭМГ",
                    section="Диагноз",
                    details="Согласно КР, при миастении рекомендована "
                    "электромиография (ритмическая стимуляция нерва) "
                    "для выявления декремента М-ответа",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-022: Ингибиторы холинэстеразы при миастении ────────────


@register_rule
class MyastheniaCholinesteraseRule(Rule):
    rule_id = "КР-022"
    rule_name = "Ингибиторы холинэстеразы при миастении"
    description = (
        "При миастении (G70) в лечении должны быть назначены "
        "антихолинэстеразные препараты"
    )
    source = _SRC_G70

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G70.search(diagnosis.text):
            return []

        treatment = parsed.sections.get("Лечение")
        treatment_text = treatment.text if treatment else ""
        epicrisis = parsed.sections.get("Эпикриз")
        epicrisis_text = epicrisis.text if epicrisis else ""
        combined = treatment_text + " " + epicrisis_text

        if not has_concept("cholinesterase_inhibitor", combined):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При миастении (G70) не найдено назначение "
                    "антихолинэстеразных препаратов",
                    section="Лечение",
                    details="Согласно КР, при миастении препаратами первой "
                    "линии являются ингибиторы холинэстеразы "
                    "(пиридостигмин / калимин)",
                    evidence=_snippet(combined),
                )
            ]
        return []


# ── КР-023: Генетическое тестирование при СМА ─────────────────


@register_rule
class SMAGeneticRule(Rule):
    rule_id = "КР-023"
    rule_name = "Генетическое тестирование при СМА"
    description = (
        "При спинальной мышечной атрофии (G12) обязательно "
        "генетическое тестирование (ген SMN1)"
    )
    source = _SRC_G12

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G12.search(diagnosis.text):
            return []

        if not has_concept("genetic_testing", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При СМА (G12) не найдено упоминание "
                    "генетического тестирования",
                    section="Диагноз",
                    details="Согласно КР, при СМА обязательно "
                    "молекулярно-генетическое исследование гена SMN1 "
                    "(ПЦР, MLPA) для подтверждения диагноза",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-024: Патогенетическая терапия при СМА ───────────────────


@register_rule
class SMAPathogeneticTherapyRule(Rule):
    rule_id = "КР-024"
    rule_name = "Патогенетическая терапия при СМА"
    description = (
        "При спинальной мышечной атрофии (G12) рекомендована "
        "патогенетическая терапия (нусинерсен / рисдиплам / золгенсма)"
    )
    source = _SRC_G12

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G12.search(diagnosis.text):
            return []

        treatment = parsed.sections.get("Лечение")
        treatment_text = treatment.text if treatment else ""
        epicrisis = parsed.sections.get("Эпикриз")
        epicrisis_text = epicrisis.text if epicrisis else ""
        combined = treatment_text + " " + epicrisis_text

        if not has_concept("nusinersen", combined):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При СМА (G12) не найдено назначение "
                    "патогенетической терапии",
                    section="Лечение",
                    details="Согласно КР, при СМА показана патогенетическая "
                    "терапия (нусинерсен / рисдиплам / золгенсма) "
                    "при наличии показаний",
                    evidence=_snippet(combined),
                )
            ]
        return []


# ── КР-025: Консультация невролога при дистонии ────────────────


@register_rule
class DystoniaNeurologistRule(Rule):
    rule_id = "КР-025"
    rule_name = "Консультация невролога при дистонии"
    description = (
        "При дистонии (G24) рекомендована консультация невролога"
    )
    source = _SRC_G24

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G24.search(diagnosis.text):
            return []

        if not has_concept("neurologist_consult", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При дистонии (G24) не найдено упоминание "
                    "консультации невролога",
                    section="Диагноз",
                    details="Согласно КР, диагностика и лечение дистонии "
                    "требуют участия невролога",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-026: Ботулинотерапия при дистонии ──────────────────────


@register_rule
class DystoniaBotulinumRule(Rule):
    rule_id = "КР-026"
    rule_name = "Ботулинотерапия при дистонии"
    description = (
        "При фокальной дистонии (G24) рекомендована "
        "ботулинотерапия как метод выбора"
    )
    source = _SRC_G24

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G24.search(diagnosis.text):
            return []

        treatment = parsed.sections.get("Лечение")
        treatment_text = treatment.text if treatment else ""
        epicrisis = parsed.sections.get("Эпикриз")
        epicrisis_text = epicrisis.text if epicrisis else ""
        combined = treatment_text + " " + epicrisis_text

        if not has_concept("botulinum_toxin", combined):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При дистонии (G24) не найдено упоминание "
                    "ботулинотерапии",
                    section="Лечение",
                    details="Согласно КР, при фокальных формах дистонии "
                    "методом выбора является ботулинотерапия "
                    "(ботулинический токсин типа А)",
                    evidence=_snippet(combined),
                )
            ]
        return []


# ── КР-027: Консультация невролога при G25 ─────────────────────


@register_rule
class ExtrapyramidalNeurologistRule(Rule):
    rule_id = "КР-027"
    rule_name = "Консультация невролога при экстрапирамидных расстройствах"
    description = (
        "При экстрапирамидных расстройствах (G25) "
        "рекомендована консультация невролога"
    )
    source = _SRC_G25

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G25.search(diagnosis.text):
            return []

        if not has_concept("neurologist_consult", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При экстрапирамидном расстройстве (G25) "
                    "не найдено упоминание консультации невролога",
                    section="Диагноз",
                    details="Согласно КР, диагностика экстрапирамидных "
                    "расстройств требует участия невролога",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-028: ЭЭГ при экстрапирамидных расстройствах ────────────


@register_rule
class ExtrapyramidalEEGRule(Rule):
    rule_id = "КР-028"
    rule_name = "ЭЭГ при экстрапирамидных расстройствах"
    description = (
        "При экстрапирамидных расстройствах (G25) рекомендовано "
        "проведение ЭЭГ для дифференциальной диагностики"
    )
    source = _SRC_G25

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G25.search(diagnosis.text):
            return []

        if not has_concept("eeg", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При экстрапирамидном расстройстве (G25) "
                    "не найдено упоминание ЭЭГ",
                    section="Диагноз",
                    details="Согласно КР, при экстрапирамидных расстройствах "
                    "рекомендовано проведение ЭЭГ для дифференциальной "
                    "диагностики с эпилептическими состояниями",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-029: Нейровизуализация при гидроцефалии ────────────────


@register_rule
class HydrocephalusImagingRule(Rule):
    rule_id = "КР-029"
    rule_name = "Нейровизуализация при гидроцефалии"
    description = (
        "При гидроцефалии (G91) обязательна нейровизуализация "
        "(МРТ, КТ или НСГ)"
    )
    source = _SRC_G91

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G91.search(diagnosis.text):
            return []

        if not (
            has_concept("mri", parsed.raw_text)
            or has_concept("ct_scan", parsed.raw_text)
            or has_concept("neurosono", parsed.raw_text)
        ):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При гидроцефалии (G91) не найдено упоминание "
                    "нейровизуализации (МРТ / КТ / НСГ)",
                    section="Диагноз",
                    details="Согласно КР, при гидроцефалии обязательна "
                    "нейровизуализация: нейросонография (НСГ), МРТ "
                    "или КТ головного мозга",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-030: Консультация офтальмолога при гидроцефалии ─────────


@register_rule
class HydrocephalusOphthalmologistRule(Rule):
    rule_id = "КР-030"
    rule_name = "Консультация офтальмолога при гидроцефалии"
    description = (
        "При гидроцефалии (G91) рекомендована консультация "
        "офтальмолога (осмотр глазного дна)"
    )
    source = _SRC_G91

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G91.search(diagnosis.text):
            return []

        if not has_concept("ophthalmologist_consult", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При гидроцефалии (G91) не найдено упоминание "
                    "консультации офтальмолога",
                    section="Диагноз",
                    details="Согласно КР, при гидроцефалии рекомендована "
                    "консультация офтальмолога для осмотра глазного дна "
                    "и исключения застойных дисков зрительных нервов",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-031: МРТ при рассеянном склерозе ────────────────────────


@register_rule
class MSMRIRule(Rule):
    rule_id = "КР-031"
    rule_name = "МРТ при рассеянном склерозе"
    description = (
        "При рассеянном склерозе (G35) обязательно проведение "
        "МРТ головного и спинного мозга"
    )
    source = _SRC_G35

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G35.search(diagnosis.text):
            return []

        if not has_concept("mri", parsed.raw_text):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MAJOR,
                    message="При рассеянном склерозе (G35) не найдено "
                    "упоминание МРТ",
                    section="Диагноз",
                    details="Согласно КР, при рассеянном склерозе обязательно "
                    "проведение МРТ головного и спинного мозга "
                    "с контрастированием",
                    evidence=_snippet(diagnosis.text),
                )
            ]
        return []


# ── КР-032: ПИТРС при рассеянном склерозе ─────────────────────


@register_rule
class MSPITRSRule(Rule):
    rule_id = "КР-032"
    rule_name = "ПИТРС при рассеянном склерозе"
    description = (
        "При рассеянном склерозе (G35) рекомендовано назначение "
        "ПИТРС (препаратов, изменяющих течение РС)"
    )
    source = _SRC_G35

    def check(self, parsed: ParseResult) -> list[Finding]:
        diagnosis = parsed.sections.get("Диагноз")
        if diagnosis is None or not _ICD_G35.search(diagnosis.text):
            return []

        treatment = parsed.sections.get("Лечение")
        treatment_text = treatment.text if treatment else ""
        epicrisis = parsed.sections.get("Эпикриз")
        epicrisis_text = epicrisis.text if epicrisis else ""
        combined = treatment_text + " " + epicrisis_text

        if not has_concept("pitrs", combined):
            return [
                Finding(
                    rule_id=self.rule_id,
                    severity=Severity.MINOR,
                    message="При рассеянном склерозе (G35) не найдено "
                    "назначение ПИТРС",
                    section="Лечение",
                    details="Согласно КР, при рассеянном склерозе "
                    "рекомендовано назначение ПИТРС (интерферон бета, "
                    "глатирамера ацетат, финголимод и др.)",
                    evidence=_snippet(combined),
                )
            ]
        return []
