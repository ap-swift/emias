"""Графический интерфейс (Tkinter) для проверки историй болезни."""

from __future__ import annotations

import os
import platform
import queue
import subprocess
import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import DISABLED, NORMAL, filedialog, messagebox

from emias_check import __version__

import emias_check.rules.order530n  # noqa: F401 — регистрация правил
import emias_check.rules.clinical  # noqa: F401

from emias_check.extractor import extract_text
from emias_check.parser import parse_sections
from emias_check.report import render_report, save_report
from emias_check.rules.base import run_all_rules

_POLL_MS = 100
_BG = "#f0f0f0"
_FONT = ("Helvetica", 13)
_FONT_BOLD = ("Helvetica", 13, "bold")


@dataclass
class _Result:
    output_path: Path
    criticals: int
    majors: int
    minors: int
    passed: int
    total: int


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"EMIAS Check v{__version__}")
        self.configure(bg=_BG)

        self._pdf_path: Path | None = None
        self._queue: queue.Queue[_Result | Exception] = queue.Queue()

        self._build_ui()

        self.update_idletasks()
        w, h = self.winfo_reqwidth() + 20, self.winfo_reqheight() + 20
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self._bring_to_front()

    # ── UI ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Title
        tk.Label(
            self,
            text="Проверка истории болезни",
            font=("Helvetica", 16, "bold"),
            bg=_BG,
            pady=12,
        ).pack()

        # File row
        row_file = tk.Frame(self, bg=_BG)
        row_file.pack(fill="x", padx=20, pady=(0, 6))

        tk.Label(row_file, text="PDF файл:", font=_FONT, bg=_BG).pack(
            side="left"
        )

        self._lbl_path = tk.Label(
            row_file,
            text="  (не выбран)  ",
            font=_FONT,
            bg="white",
            relief="sunken",
            anchor="w",
            padx=6,
            pady=4,
            width=36,
        )
        self._lbl_path.pack(side="left", padx=(8, 8), fill="x", expand=True)

        self._btn_select = tk.Button(
            row_file,
            text="Выбрать PDF…",
            font=_FONT,
            command=self._on_select,
            padx=10,
            pady=4,
        )
        self._btn_select.pack(side="left")

        # Check button row
        row_check = tk.Frame(self, bg=_BG)
        row_check.pack(fill="x", padx=20, pady=8)

        self._btn_check = tk.Button(
            row_check,
            text="   Проверить   ",
            font=_FONT_BOLD,
            command=self._on_check,
            state=DISABLED,
            padx=16,
            pady=6,
            bg="#4a90d9",
            fg="white",
            activebackground="#3a7bc8",
            activeforeground="white",
            disabledforeground="#aaaaaa",
        )
        self._btn_check.pack()

        # Progress
        self._progress_var = tk.IntVar(value=0)
        self._progress_running = False

        row_prog = tk.Frame(self, bg=_BG)
        row_prog.pack(fill="x", padx=20, pady=(4, 0))

        self._canvas = tk.Canvas(
            row_prog, height=8, bg="#dddddd", highlightthickness=0
        )
        self._canvas.pack(fill="x")
        self._prog_rect = self._canvas.create_rectangle(
            0, 0, 0, 8, fill="#4a90d9", width=0
        )

        # Status
        self._lbl_status = tk.Label(
            self,
            text="Выберите PDF-файл истории болезни для проверки.",
            font=("Helvetica", 11),
            bg=_BG,
            fg="gray",
            wraplength=500,
            pady=10,
        )
        self._lbl_status.pack(fill="x", padx=20)

    # ── Window management ──────────────────────────────────────

    def _bring_to_front(self) -> None:
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))
        self.focus_force()
        if platform.system() == "Darwin":
            try:
                subprocess.Popen(
                    [
                        "osascript", "-e",
                        'tell application "System Events" to set frontmost '
                        f'of the first process whose unix id is {os.getpid()} '
                        'to true',
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                pass

    # ── Progress bar animation (pure Canvas) ───────────────────

    def _start_progress(self) -> None:
        self._progress_running = True
        self._progress_pos = 0
        self._progress_dir = 1
        self._animate_progress()

    def _animate_progress(self) -> None:
        if not self._progress_running:
            return
        cw = self._canvas.winfo_width()
        bar_w = max(cw // 4, 40)
        self._progress_pos += self._progress_dir * 6
        if self._progress_pos + bar_w >= cw:
            self._progress_dir = -1
        elif self._progress_pos <= 0:
            self._progress_dir = 1
        self._canvas.coords(
            self._prog_rect,
            self._progress_pos, 0,
            self._progress_pos + bar_w, 8,
        )
        self.after(30, self._animate_progress)

    def _stop_progress(self) -> None:
        self._progress_running = False
        self._canvas.coords(self._prog_rect, 0, 0, 0, 8)

    # ── Callbacks ──────────────────────────────────────────────

    def _on_select(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите PDF-файл",
            filetypes=[("PDF файлы", "*.pdf"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        self._pdf_path = Path(path)
        display = self._pdf_path.name
        if len(display) > 45:
            display = "…" + display[-42:]
        self._lbl_path.configure(text=f"  {display}  ")
        self._btn_check.configure(state=NORMAL)
        self._lbl_status.configure(
            text="Нажмите «Проверить» для запуска.", fg="gray"
        )

    def _on_check(self) -> None:
        if self._pdf_path is None:
            return
        self._btn_check.configure(state=DISABLED)
        self._btn_select.configure(state=DISABLED)
        self._start_progress()
        self._lbl_status.configure(text="Проверка…", fg="black")

        t = threading.Thread(
            target=self._run_pipeline, args=(self._pdf_path,), daemon=True
        )
        t.start()
        self.after(_POLL_MS, self._poll_result)

    # ── Pipeline ───────────────────────────────────────────────

    def _run_pipeline(self, pdf_path: Path) -> None:
        try:
            extraction = extract_text(pdf_path)
            page_texts = [p.text for p in extraction.pages]
            parsed = parse_sections(extraction.full_text, page_texts)
            check_report = run_all_rules(parsed)

            html = render_report(
                check_report=check_report,
                parsed=parsed,
                source_name=pdf_path.name,
                num_pages=extraction.num_pages,
            )
            output = pdf_path.parent / f"report_{pdf_path.stem}.html"
            save_report(html, output)

            self._queue.put(
                _Result(
                    output_path=output,
                    criticals=len(check_report.criticals),
                    majors=len(check_report.majors),
                    minors=len(check_report.minors),
                    passed=check_report.passed_rules,
                    total=check_report.total_rules,
                )
            )
        except Exception as exc:
            self._queue.put(exc)

    def _poll_result(self) -> None:
        try:
            result = self._queue.get_nowait()
        except queue.Empty:
            self.after(_POLL_MS, self._poll_result)
            return

        self._stop_progress()
        self._btn_select.configure(state=NORMAL)

        if isinstance(result, Exception):
            self._lbl_status.configure(text="Ошибка при проверке.", fg="red")
            messagebox.showerror(
                "Ошибка", f"Не удалось проверить PDF:\n\n{result}"
            )
            self._btn_check.configure(state=NORMAL)
            return

        self._lbl_status.configure(
            text=(
                f"Готово ({result.passed}/{result.total} правил).  "
                f"Крит: {result.criticals}  Сущ: {result.majors}  "
                f"Форм: {result.minors}.  Отчёт открыт."
            ),
            fg="#2e7d32" if result.criticals == 0 else "red",
        )
        self._btn_check.configure(state=NORMAL)
        webbrowser.open(result.output_path.as_uri())


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
