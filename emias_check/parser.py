"""Разбиение текста истории болезни на именованные разделы."""

from __future__ import annotations

import re

from emias_check.models import ParseResult, SectionContent

# Канонические названия разделов и их regex-паттерны.
# Порядок важен: специфичные паттерны идут до общих, иначе общий
# паттерн (например, "диагноз") поглотит "предварительный диагноз".
_I = re.IGNORECASE
_IM = re.IGNORECASE | re.MULTILINE

SECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # ── Идентификация ──
    (
        "Паспортная часть",
        re.compile(
            r"(?:паспортная\s+часть|общие\s+сведения|сведения\s+о\s+(?:пациенте|больном))",
            _I,
        ),
    ),
    (
        "Дата и время поступления",
        re.compile(
            r"(?:дата\s+и?\s*врем[яе]\s+поступлени|дата\s+поступлени)",
            _I,
        ),
    ),
    # ── Жалобы / анамнезы ──
    (
        "Жалобы",
        re.compile(
            r"(?:жалобы\s+при\s+поступлении|жалобы\s+на\s+момент|предъявляет\s+жалобы|жалобы)",
            _I,
        ),
    ),
    (
        "Анамнез заболевания",
        re.compile(
            r"(?:анамнез\s+(?:заболевания|болезни|настоящего\s+заболевания)"
            r"|anamnesis\s+morbi|история\s+настоящего\s+заболевания)",
            _I,
        ),
    ),
    (
        "Анамнез жизни",
        re.compile(
            r"(?:анамнез\s+жизни|anamnesis\s+vitae"
            r"|перенесённые\s+заболевани|перенесенные\s+заболевани"
            r"|сведения\s+о\s+жизни)",
            _I,
        ),
    ),
    (
        "Аллергологический анамнез",
        re.compile(
            r"(?:аллерг\w+\s+анамнез|аллергоанамнез|лекарственн\w+\s+неперенос"
            r"|лекарственн\w+\s+аллерги)",
            _I,
        ),
    ),
    # ── Осмотр ──
    (
        "Первичный осмотр",
        re.compile(
            r"(?:первичн\w+\s+осмотр|осмотр\s+(?:врача\s+)?приёмного"
            r"|осмотр\s+(?:врача\s+)?приемного|осмотр\s+при\s+поступлени)",
            _I,
        ),
    ),
    (
        "Объективный статус",
        re.compile(
            r"(?:объективн\w+\s+(?:статус|осмотр|данные)|status\s+praesens"
            r"|физикальн\w+\s+обследован|объективно(?:\s|$)"
            r"|данные\s+объективного\s+осмотра)",
            _I,
        ),
    ),
    # ── Диагноз (специфичные → общий) ──
    (
        "Предварительный диагноз",
        re.compile(r"^предварительн\w+\s+диагноз", _IM),
    ),
    (
        "Обоснование предварительного диагноза",
        re.compile(
            r"^обоснование\s+(?:предварительного\s+|клинического\s+)?диагноз",
            _IM,
        ),
    ),
    (
        "Обоснование госпитализации",
        re.compile(
            r"(?:обоснование\s+госпитализаци|показани\w+\s+к\s+госпитализац"
            r"|госпитализация\s+показана|нуждается\s+в\s+стационарн)",
            _I,
        ),
    ),
    (
        "Клинический диагноз",
        re.compile(r"^клинически\w+\s+диагноз", _IM),
    ),
    (
        "Диагноз",
        re.compile(r"(?:заключительн\w+\s+)?диагноз", _I),
    ),
    # ── Обследования и лечение ──
    (
        "План обследования",
        re.compile(
            r"(?:план\s+(?:обследовани|диагностических\s+мероприятий"
            r"|лечебно-диагностических\s+мероприятий)"
            r"|назначено\s+обследовани)",
            _I,
        ),
    ),
    (
        "Результаты обследований",
        re.compile(
            r"результат\w*\s+(?:обследовани|лабораторн|инструментальн)",
            _I,
        ),
    ),
    (
        "План лечения",
        re.compile(
            r"(?:^план\s+лечени|лечебн\w+\s+тактик|план\s+ведени"
            r"|рекомендовано\s+лечени)",
            _IM,
        ),
    ),
    (
        "Назначения",
        re.compile(
            r"(?:^назначени|лист\s+назначени)",
            _IM,
        ),
    ),
    (
        "Лечение",
        re.compile(
            r"(?:^лечение$|медикаментозн\w+\s+(?:лечение|терапия))",
            _IM,
        ),
    ),
    # ── Дневники ──
    (
        "Дневники",
        re.compile(
            r"(?:дневник\w*(?:\s+запис\w*)?|дневниковая\s+запис"
            r"|запис\w+\s+лечащего\s+врач|осмотр\s+в\s+динамик)",
            _I,
        ),
    ),
    # ── Эпикризы (специфичные → общий) ──
    (
        "Этапный эпикриз",
        re.compile(r"этапн\w+\s+(?:клинич\w+\s+)?эпикриз", _I),
    ),
    (
        "Эпикриз",
        re.compile(
            r"(?:выписной\s+эпикриз|эпикриз|выписка|выписной\s+документ)",
            _I,
        ),
    ),
    # ── ИДС, подписи ──
    (
        "Информированное согласие",
        re.compile(
            r"(?:информированное\s+(?:добровольное\s+)?согласие|\bидс\b)",
            _I,
        ),
    ),
    (
        "Подписи",
        re.compile(r"^подпис", _IM),
    ),
]


def _find_section_boundaries(
    text: str,
) -> list[tuple[str, int, str]]:
    """Найти позиции начала каждого раздела в тексте.

    Returns:
        Список кортежей (каноническое_имя, позиция, оригинальный_заголовок).
    """
    boundaries: list[tuple[str, int, str]] = []
    seen_names: set[str] = set()

    for name, pattern in SECTION_PATTERNS:
        for match in pattern.finditer(text):
            line_start = text.rfind("\n", 0, match.start()) + 1
            prefix = text[line_start : match.start()].strip()
            if len(prefix) > 20:
                continue
            if name not in seen_names:
                boundaries.append((name, match.start(), match.group()))
                seen_names.add(name)

    boundaries.sort(key=lambda x: x[1])
    return boundaries


def _estimate_page(text: str, position: int, page_texts: list[str]) -> int | None:
    """Примерно определить номер страницы по позиции в полном тексте."""
    if not page_texts:
        return None
    offset = 0
    for i, pt in enumerate(page_texts):
        end = offset + len(pt)
        if position < end:
            return i + 1
        offset = end + 1  # +1 for the joining newline
    return len(page_texts)


def parse_sections(
    text: str,
    page_texts: list[str] | None = None,
) -> ParseResult:
    """Разбить текст истории болезни на именованные разделы.

    Args:
        text: полный текст документа.
        page_texts: тексты отдельных страниц (для определения номера страницы).

    Returns:
        ParseResult с найденными разделами.
    """
    result = ParseResult(raw_text=text)
    boundaries = _find_section_boundaries(text)

    if not boundaries:
        result.sections["Нераспознанный текст"] = SectionContent(
            name="Нераспознанный текст",
            text=text.strip(),
            found=True,
            start_pos=0,
        )
        return result

    # Текст до первого раздела (если есть)
    first_start = boundaries[0][1]
    preamble = text[:first_start].strip()
    if preamble:
        result.sections["Преамбула"] = SectionContent(
            name="Преамбула",
            text=preamble,
            found=True,
            start_pos=0,
            page_hint=_estimate_page(text, 0, page_texts or []),
        )

    for i, (name, start, original_heading) in enumerate(boundaries):
        if i + 1 < len(boundaries):
            end = boundaries[i + 1][1]
        else:
            end = len(text)

        section_text = text[start:end].strip()
        result.sections[name] = SectionContent(
            name=name,
            text=section_text,
            found=True,
            source_heading=original_heading,
            start_pos=start,
            page_hint=_estimate_page(text, start, page_texts or []),
        )

    return result
