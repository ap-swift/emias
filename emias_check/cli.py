"""CLI-интерфейс для проверки историй болезни."""

from __future__ import annotations

from pathlib import Path

import click

from emias_check import __version__

import emias_check.rules.order530n  # noqa: F401
import emias_check.rules.clinical  # noqa: F401

from emias_check.extractor import extract_text
from emias_check.parser import parse_sections
from emias_check.report import render_report, render_json_report, save_report
from emias_check.rules.base import run_all_rules


def _process_single_pdf(
    pdf_path: Path,
    output_path: Path | None,
    fmt: str = "html",
) -> Path:
    """Обработать один PDF-файл и вернуть путь к отчёту."""
    click.echo(f"  Извлечение текста из {pdf_path.name}...")
    extraction = extract_text(pdf_path)
    click.echo(f"  Страниц: {extraction.num_pages}")

    click.echo("  Разбиение на разделы...")
    page_texts = [p.text for p in extraction.pages]
    parsed = parse_sections(extraction.full_text, page_texts)
    click.echo(f"  Найдено разделов: {len(parsed.sections)} ({', '.join(parsed.found_section_names)})")

    click.echo("  Проверка правил...")
    check_report = run_all_rules(parsed)

    c = len(check_report.criticals)
    m = len(check_report.majors)
    n = len(check_report.minors)
    click.echo(
        f"  Результат: {check_report.passed_rules}/{check_report.total_rules} правил пройдено, "
        f"{c} крит., {m} сущ., {n} форм."
    )

    render_fn = render_json_report if fmt == "json" else render_report
    content = render_fn(
        check_report=check_report,
        parsed=parsed,
        source_name=pdf_path.name,
        num_pages=extraction.num_pages,
    )

    if output_path is None:
        ext = ".json" if fmt == "json" else ".html"
        output_path = pdf_path.parent / f"report_{pdf_path.stem}{ext}"

    save_report(content, output_path)
    click.echo(f"  Отчёт сохранён: {output_path}")
    return output_path


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Путь для сохранения отчёта (по умолчанию: report_<имя>.<формат> рядом с PDF).",
)
@click.option(
    "--format", "-f", "fmt",
    type=click.Choice(["html", "json"], case_sensitive=False),
    default="html",
    help="Формат отчёта: html (по умолчанию) или json.",
)
@click.version_option(version=__version__, prog_name="emias-check")
def main(path: Path, output: Path | None, fmt: str) -> None:
    """Проверка историй болезни по приказу 530н.

    PATH -- путь к PDF-файлу или папке с PDF-файлами.
    """
    click.echo(f"EMIAS Check v{__version__}")
    click.echo("=" * 50)

    if path.is_file():
        if not path.suffix.lower() == ".pdf":
            raise click.BadParameter(f"Ожидается PDF-файл, получен: {path.suffix}")
        _process_single_pdf(path, output, fmt)

    elif path.is_dir():
        pdf_files = sorted(path.glob("*.pdf"))
        if not pdf_files:
            click.echo(f"В папке {path} не найдено PDF-файлов.")
            raise SystemExit(1)

        click.echo(f"Найдено PDF-файлов: {len(pdf_files)}\n")
        if output is not None:
            click.echo("Внимание: --output игнорируется при обработке папки.\n")

        all_ok = True
        for pdf_file in pdf_files:
            click.echo(f"\n--- {pdf_file.name} ---")
            try:
                _process_single_pdf(pdf_file, output_path=None, fmt=fmt)
            except Exception as exc:
                click.echo(f"  ОШИБКА: {exc}", err=True)
                all_ok = False

        if all_ok:
            click.echo(f"\nВсе {len(pdf_files)} файлов обработаны успешно.")
        else:
            click.echo("\nОбработка завершена с ошибками.", err=True)
    else:
        raise click.BadParameter(f"Путь не найден: {path}")
