"""Извлечение текста из PDF-файлов историй болезни."""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from emias_check.models import ExtractionResult, PageText


def is_scanned_pdf(pdf_path: Path) -> bool:
    """Определить, является ли PDF сканом (без текстового слоя).

    Returns:
        True если PDF не содержит извлекаемого текста.
    """
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)
    total_chars = sum(len(page.get_text("text").strip()) for page in doc)
    doc.close()
    return total_chars == 0


def _extract_with_pymupdf(pdf_path: Path) -> list[PageText]:
    """Извлечь текст через PyMuPDF (основной метод)."""
    doc = fitz.open(pdf_path)
    pages: list[PageText] = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        pages.append(PageText(page_number=page_num, text=text))
    doc.close()
    return pages


def _extract_with_pdfplumber(pdf_path: Path) -> list[PageText]:
    """Извлечь текст через pdfplumber (fallback)."""
    import pdfplumber

    pages: list[PageText] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(PageText(page_number=page_num, text=text))
    return pages


def extract_text(pdf_path: Path) -> ExtractionResult:
    """Извлечь текст из PDF-файла.

    Сначала пробует PyMuPDF, при неудаче — pdfplumber (если установлен).

    Args:
        pdf_path: путь к PDF-файлу.

    Returns:
        ExtractionResult с текстом постранично.

    Raises:
        FileNotFoundError: файл не найден.
        RuntimeError: не удалось прочитать PDF или PDF является сканом.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Файл не найден: {pdf_path}")

    try:
        pages = _extract_with_pymupdf(pdf_path)
    except Exception as exc:
        raise RuntimeError(f"Не удалось открыть PDF: {pdf_path}") from exc

    full_text = "\n".join(p.text for p in pages)

    if not full_text.strip():
        try:
            pages = _extract_with_pdfplumber(pdf_path)
            full_text = "\n".join(p.text for p in pages)
        except ImportError:
            pass
        except Exception:
            pass

    result = ExtractionResult(source_path=pdf_path, pages=pages)

    if not result.full_text.strip():
        raise RuntimeError(
            f"PDF не содержит текстового слоя. Нужен OCR-модуль: {pdf_path}"
        )

    return result
