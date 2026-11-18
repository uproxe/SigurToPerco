"""Проверка генерации картинок для интерфейса (без запуска окна)."""
import os
import struct
import sys
import zlib

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
pytest.importorskip("tkinter")

from sigur_perco import widgets  # noqa: E402


def decode_png(data):
    """-> (ширина, высота, распакованные строки) с проверкой структуры файла."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, chunks = 8, {}
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        crc = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])[0]
        assert crc == zlib.crc32(kind + body) & 0xFFFFFFFF, kind
        chunks[kind] = body
        pos += 12 + length
    w, h, depth, color = struct.unpack(">IIBB", chunks[b"IHDR"][:10])
    assert (depth, color) == (8, 2)                      # 8 бит, RGB
    raw = zlib.decompress(chunks[b"IDAT"])
    assert len(raw) == h * (1 + 3 * w)
    return w, h, raw


@pytest.mark.parametrize("w, h, r, border", [(120, 34, 8, None), (40, 20, 10, "#E0E6E8"), (9, 9, 12, "#000000")])
def test_rounded_png(w, h, r, border):
    rows = widgets.rounded_rows(w, h, r, "#0D9488", "#FFFFFF", border)
    assert len(rows) == h and all(len(row) == 3 * w for row in rows)
    assert decode_png(widgets.png_bytes(w, h, rows))[:2] == (w, h)


def test_corner_matches_rect():
    corner = widgets.corner_rows(12, "#FFFFFF", "#F2F5F6", "#E0E6E8")
    rect = widgets.rounded_rows(100, 60, 12, "#FFFFFF", "#F2F5F6", "#E0E6E8")
    assert all(rect[y][:36] == corner[y] for y in range(12))
    # самый угловой пиксель - цвет фона снаружи, центр - цвет заливки
    assert rect[0][:3] == bytes((0xF2, 0xF5, 0xF6))
    assert rect[30][150:153] == bytes((0xFF, 0xFF, 0xFF))


def test_toggle_knob_moves():
    off = widgets.toggle_rows(34, 20, 0.0, "#C9D2D5", "#FFFFFF", "#FFFFFF")
    on = widgets.toggle_rows(34, 20, 1.0, "#0D9488", "#FFFFFF", "#FFFFFF")
    white = bytes((255, 255, 255))
    # ручка (белая) слева в выключенном состоянии и справа - во включённом
    assert off[10][3 * 9:3 * 10] == white and on[10][3 * 24:3 * 25] == white
    assert on[10][3 * 9:3 * 10] != white
