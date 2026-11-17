#!/usr/bin/env python3
"""Создаёт examples/sigur_export_sample.xlsx - вымышленную выгрузку для проб.

    python scripts/make_sample.py
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))

from sample_export import write_sample_xlsx  # noqa: E402

if __name__ == "__main__":
    out = os.path.join(ROOT, "examples", "sigur_export_sample.xlsx")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write_sample_xlsx(out)
    print("Готово:", out)
