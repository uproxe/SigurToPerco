"""Точка входа: окно программы или консольный режим.

    python -m sigur_perco                      # окно
    python -m sigur_perco export.xls           # окно, файл сразу сконвертирован
    python -m sigur_perco --card 000000AB12CD34
    python -m sigur_perco --cli export.xls -o userPERCO.xlsx [--until "..."] [--upper]
"""

import argparse
import os
import sys
import traceback

from . import APP_NAME, __version__, core


def notify(title, message, error=False):
    """Окошко с сообщением (если окна недоступны - печать в консоль)."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        (messagebox.showerror if error else messagebox.showinfo)(title, message)
        r.destroy()
    except Exception:
        print(title + "\n" + message)


def build_parser():
    p = argparse.ArgumentParser(prog="SigurPerco",
                                description="Sigur -> PERCo: пересчёт пропусков и выгрузки сотрудников")
    p.add_argument("files", nargs="*", help="выгрузка(и) из Sigur (.xls / .xlsx)")
    p.add_argument("--cli", action="store_true", help="без окна: сконвертировать файлы и выйти")
    p.add_argument("-o", "--output", help="куда сохранить результат (только для одного файла; включает --cli)")
    p.add_argument("--until", default=core.UNLIMITED_UNTIL,
                   help="«Действует до» для пропусков без срока (по умолчанию %s)" % core.UNLIMITED_UNTIL)
    p.add_argument("--upper", action="store_true", default=core.UPPERCASE_NAMES, help="ФИО заглавными буквами")
    p.add_argument("--card", metavar="НОМЕР", help="пересчитать один номер пропуска и выйти")
    p.add_argument("--version", action="version", version="%(prog)s " + __version__)
    return p


def main(argv=None):
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
        except Exception:
            pass

    args = build_parser().parse_args(argv)

    if args.card:
        try:
            print(core.convert_any(args.card))
            return 0
        except ValueError as e:
            print("ОШИБКА:", e)
            return 1

    if not (args.cli or args.output):
        from .gui import run_gui
        run_gui(args.files[0] if args.files else None)
        return 0

    if not args.files:
        print("Укажите файл выгрузки из Sigur.")
        return 2
    if args.output and len(args.files) > 1:
        notify(APP_NAME, "Параметр -o можно использовать только с одним файлом.", error=True)
        return 2

    messages, failed = [], False
    for src in args.files:
        try:
            res = core.convert_file(src, args.output, until=args.until, upper=args.upper)
            msg = os.path.basename(src) + "\n" + res.summary()
            if res.warnings:
                msg += "\n\nПредупреждения:\n" + "\n".join("- " + w for w in res.warnings)
            messages.append(msg)
        except Exception as e:
            failed = True
            messages.append("%s\nОШИБКА: %s" % (os.path.basename(src), e))

    report = "\n\n".join(messages)
    if sys.stdout is None:                 # собранная оконная программа - консоли нет
        notify(APP_NAME, report, error=failed)
    else:
        print(report)
    return 1 if failed else 0


def run():
    """Запуск с записью непредвиденных ошибок в лог рядом с программой."""
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        err = traceback.format_exc()
        try:
            log_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            if not os.access(log_dir, os.W_OK):
                log_dir = os.path.expanduser("~")
            with open(os.path.join(log_dir, "SigurPerco_error.log"), "w", encoding="utf-8") as f:
                f.write(err)
        except Exception:
            pass
        notify(APP_NAME + ": непредвиденная ошибка", err[-1500:], error=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
