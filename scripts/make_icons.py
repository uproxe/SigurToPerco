#!/usr/bin/env python3
"""Рисует значок программы во всех нужных форматах.

    python scripts/make_icons.py

Нужен только Pillow (pip install pillow). Результат:
    assets/icon.ico          - Windows (16…256 px)
    assets/icon.icns         - macOS
    assets/icons/<N>.png     - Linux и окно программы (16…512 px)
    assets/icon-preview.png  - картинка для README

Значок: бесконтактный пропуск («ракушка» с прорезью под ленту) и стрелки
пересчёта. Цвета и пропорции - в константах ниже.
"""
import os

from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ASSETS = os.path.join(ROOT, "assets")

BG_TOP = "#14B8A6"       # фон: сверху
BG_BOTTOM = "#0F766E"    # фон: снизу
CARD = "#FFFFFF"         # пропуск
INK = "#0F766E"          # прорезь и стрелки


def rgba(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def background(S):
    """Скруглённый квадрат с вертикальным градиентом."""
    top, bottom = rgba(BG_TOP), rgba(BG_BOTTOM)
    grad = Image.new("RGBA", (1, S))
    for y in range(S):
        t = y / (S - 1)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(4)))
    grad = grad.resize((S, S))
    mask = Image.new("L", (S, S), 0)
    m = 0.03 * S
    ImageDraw.Draw(mask).rounded_rectangle([m, m, S - m, S - m], radius=0.225 * S, fill=255)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)
    return img


def arrows(d, cx, cy, w, gap, lw, head, col):
    """Две стрелки: верхняя вправо, нижняя влево."""
    y1, y2 = cy - gap / 2, cy + gap / 2
    d.line([cx - w / 2, y1, cx + w / 2 - head * 0.6, y1], fill=col, width=lw)
    d.polygon([(cx + w / 2, y1), (cx + w / 2 - head, y1 - head * 0.75),
               (cx + w / 2 - head, y1 + head * 0.75)], fill=col)
    d.line([cx - w / 2 + head * 0.6, y2, cx + w / 2, y2], fill=col, width=lw)
    d.polygon([(cx - w / 2, y2), (cx - w / 2 + head, y2 - head * 0.75),
               (cx - w / 2 + head, y2 + head * 0.75)], fill=col)


def draw(S, small=False):
    img = background(S)
    d = ImageDraw.Draw(img)
    ink = rgba(INK)

    cw, ch = (0.72 if small else 0.64) * S, (0.48 if small else 0.42) * S
    x0, y0 = (S - cw) / 2, (S - ch) / 2
    d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=0.06 * S, fill=rgba(CARD))

    sw, sh = (0.06 if small else 0.035) * S, (0.20 if small else 0.13) * S
    sx = x0 + (0.07 if small else 0.06) * S
    d.rounded_rectangle([sx, S / 2 - sh / 2, sx + sw, S / 2 + sh / 2], radius=sw / 2, fill=ink)

    if small:
        # на 16-24 px две стрелки сливаются - оставляем одну жирную
        lw = max(1, int(0.07 * S))
        cx, w, head = S / 2 + 0.08 * S, 0.30 * S, 0.11 * S
        d.line([cx - w / 2, S / 2, cx + w / 2 - head * 0.5, S / 2], fill=ink, width=lw)
        d.polygon([(cx + w / 2, S / 2), (cx + w / 2 - head, S / 2 - head),
                   (cx + w / 2 - head, S / 2 + head)], fill=ink)
    else:
        arrows(d, S / 2 + 0.05 * S, S / 2, 0.26 * S, 0.11 * S, max(1, int(0.03 * S)), 0.05 * S, ink)
    return img


def render(size):
    """Рисуем крупно и уменьшаем - так края получаются гладкими."""
    big = draw(min(size * 4, 2048), small=size <= 24)
    return big.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(os.path.join(ASSETS, "icons"), exist_ok=True)
    png_sizes = [16, 24, 32, 48, 64, 128, 256, 512]
    imgs = {s: render(s) for s in png_sizes + [20, 40, 1024]}

    for s in png_sizes:
        imgs[s].save(os.path.join(ASSETS, "icons", "%d.png" % s), optimize=True)

    ico_sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    imgs[256].save(os.path.join(ASSETS, "icon.ico"), format="ICO",
                   sizes=[(s, s) for s in ico_sizes],
                   append_images=[imgs[s] for s in ico_sizes if s != 256])

    imgs[1024].save(os.path.join(ASSETS, "icon.icns"), format="ICNS",
                    append_images=[imgs[s] for s in (16, 32, 64, 128, 256, 512)])

    shown = [256, 128, 64, 48, 32, 16]
    prev = Image.new("RGBA", (sum(shown) + 24 * (len(shown) + 1), 256 + 48), (0, 0, 0, 0))
    x = 24
    for s in shown:
        prev.alpha_composite(imgs[s], (x, 256 + 24 - s))
        x += s + 24
    prev.save(os.path.join(ASSETS, "icon-preview.png"), optimize=True)
    print("Значки сохранены в", os.path.abspath(ASSETS))


if __name__ == "__main__":
    main()
