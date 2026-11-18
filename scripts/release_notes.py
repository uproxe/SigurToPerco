#!/usr/bin/env python3
"""Описание релиза из CHANGELOG.md и проверка версии перед выпуском.

    python scripts/release_notes.py 0.3.0            # описание релиза -> stdout
    python scripts/release_notes.py 0.3.0 --check    # проверить, что версия готова к выпуску
    python scripts/release_notes.py --check          # то же для версии из sigur_perco/__init__.py
    python scripts/release_notes.py --print-version  # версия из sigur_perco/__init__.py

--check завершается с ошибкой, если версия в sigur_perco/__init__.py не совпадает
с указанной или в CHANGELOG.md нет раздела для неё.
"""

import argparse
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def code_version():
    m = re.search(r'__version__\s*=\s*"([^"]+)"', read("sigur_perco", "__init__.py"))
    return m.group(1) if m else ""


def changelog_section(version):
    """Текст раздела «## [версия] - дата» без заголовка, или None."""
    text = read("CHANGELOG.md")
    m = re.search(r"^## \[%s\][^\n]*\n(.*?)(?=^## \[|^\[[^\]]+\]: )" % re.escape(version), text, re.M | re.S)
    return m.group(1).strip() if m else None


def main():
    for stream in (sys.stdout, sys.stderr):        # русский текст в консоли Windows
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("version", nargs="?", help="версия без «v», например 0.3.0 (по умолчанию - из кода)")
    ap.add_argument("--check", action="store_true", help="только проверить готовность к выпуску")
    ap.add_argument("--print-version", action="store_true", help="напечатать версию из кода и выйти")
    args = ap.parse_args()
    if args.print_version:
        print(code_version())
        return 0
    version = (args.version or code_version()).lstrip("v")

    section = changelog_section(version)
    problems = []
    if code_version() != version:
        problems.append("в sigur_perco/__init__.py версия %r, а выпускается %r" % (code_version(), version))
    if not section:
        problems.append("в CHANGELOG.md нет раздела «## [%s] - ГГГГ-ММ-ДД» с описанием" % version)

    if args.check:
        if problems:
            print("Версия не готова к выпуску:\n- " + "\n- ".join(problems), file=sys.stderr)
            return 1
        print("Версия %s готова к выпуску" % version)
        return 0

    downloads = read(".github", "release-notes.md").strip()
    print("%s\n\n%s" % (section or "", downloads))
    return 0


if __name__ == "__main__":
    sys.exit(main())
