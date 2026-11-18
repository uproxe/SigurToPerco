#!/usr/bin/env python3
"""Запускает настоящее окно программы, прокликивает обе вкладки и сохраняет скриншоты.

Это проверка интерфейса «вживую»: если при построении окна или в обработчиках
возникнет ошибка Tk, скрипт завершится с ошибкой.

    python scripts/screenshots.py [папка]          # по умолчанию screenshots/

На GitHub Actions запускается на Linux под виртуальным экраном (Xvfb):
    xvfb-run -a -s "-screen 0 1440x1000x24" python scripts/screenshots.py

Нужен Pillow (pip install pillow) - им делается снимок экрана.
"""

import os
import sys
import tempfile
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from sample_export import write_sample_xlsx  # noqa: E402

from sigur_perco import gui  # noqa: E402

STEP_MS = 900


def main():
    out_dir = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "screenshots"))
    os.makedirs(out_dir, exist_ok=True)
    work = tempfile.mkdtemp(prefix="sigurperco-")
    sample = write_sample_xlsx(os.path.join(work, "sigur_export_sample.xlsx"))

    errors, saved = [], []

    # в автоматическом прогоне окна с ошибками не показываем - просто запоминаем
    from tkinter import messagebox
    messagebox.showerror = lambda *a, **k: errors.append("messagebox: %s" % (a,))

    def on_ready(api):
        root = api.root

        def report(exc, val, tb):
            errors.append("".join(traceback.format_exception(exc, val, tb)))
            root.destroy()
        root.report_callback_exception = report

        def shot(name):
            from PIL import ImageGrab
            root.update()
            x, y = root.winfo_rootx(), root.winfo_rooty()
            w, h = root.winfo_width(), root.winfo_height()
            path = os.path.join(out_dir, name)
            # на Linux снимаем напрямую с X-сервера (Xvfb), без gnome-screenshot и т.п.
            extra = {"xdisplay": os.environ.get("DISPLAY")} if sys.platform.startswith("linux") else {}
            ImageGrab.grab(bbox=(x, y, x + w, y + h), **extra).save(path)
            saved.append(path)
            print("снимок:", path, "(%dx%d)" % (w, h), flush=True)

        steps = [
            lambda: (api.show_tab("card"), api.set_card("000000AB12CD34"), api.copy_current(),
                     api.set_batch("000000AB12CD34\n000000AB0A1B2C\n18/52532\nне номер"), api.convert_batch()),
            lambda: shot("1-card.png"),
            lambda: api.open_file(sample),
            lambda: shot("2-export-preview.png"),
            lambda: api.show_view("warn"),
            lambda: shot("3-export-warnings.png"),
            root.destroy,
        ]

        def run_step(i=0):
            if i >= len(steps):
                return
            try:
                steps[i]()
            except Exception:
                errors.append(traceback.format_exc())
                root.destroy()
                return
            root.after(STEP_MS, run_step, i + 1)

        run_step()

    gui.run_gui(on_ready=on_ready)

    if errors:
        print("\nОШИБКИ ИНТЕРФЕЙСА:\n" + "\n".join(errors), file=sys.stderr)
        return 1
    if len(saved) != 3:
        print("Сделано снимков: %d из 3" % len(saved), file=sys.stderr)
        return 1
    print("Интерфейс в порядке, снимков: %d" % len(saved))
    return 0


if __name__ == "__main__":
    sys.exit(main())
