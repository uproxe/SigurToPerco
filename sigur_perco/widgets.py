"""Современные элементы интерфейса для tkinter - без сторонних библиотек.

Стандартные виджеты Tk выглядят как в начале 2000-х, а штатная отрисовка скруглений
на холсте получается «лесенкой». Поэтому скругления здесь рисуются картинками PNG,
которые модуль сам генерирует со сглаживанием (антиалиасингом):

    Painter        - рисует и кэширует картинки (скруглённые прямоугольники, углы, переключатели)
    RoundedFrame   - рамка-карточка со скруглёнными углами (обычный Frame + 4 картинки-уголка)
    RoundButton    - скруглённая кнопка с подсветкой при наведении
    Toggle         - переключатель вместо старой «галочки»
    ScrollBar      - тонкая полоса прокрутки, которая прячется, когда прокручивать нечего

Цвета задаются строками "#RRGGBB".
"""

import base64
import math
import struct
import zlib

import tkinter as tk
import tkinter.font as tkfont


# =====================================================================
#  Рисование PNG
# =====================================================================

def _rgb(color):
    c = color.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def _clamp(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def _blend(*layers):
    """Смешивание цветов: _blend((цвет, доля), (цвет, доля), ...), доли в сумме = 1."""
    return bytes(int(round(sum(c[i] * a for c, a in layers))) for i in range(3))


def png_bytes(width, height, rows):
    """rows - список строк пикселей по 3 байта (RGB) -> содержимое PNG-файла."""
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6))
            + chunk(b"IEND", b""))


def _flip(row):
    """Отразить строку пикселей слева направо."""
    return b"".join(row[i:i + 3] for i in range(len(row) - 3, -1, -3))


def corner_rows(r, fill, outer, border=None, bw=1):
    """Левый верхний уголок r x r: снаружи - outer, дуга - border, внутри - fill."""
    f, o = _rgb(fill), _rgb(outer)
    b = _rgb(border) if border else f
    rows = []
    for y in range(r):
        row = bytearray()
        for x in range(r):
            d = math.hypot(r - (x + 0.5), r - (y + 0.5)) - r       # < 0 внутри дуги
            shape = _clamp(0.5 - d)
            inner = _clamp(0.5 - (d + bw)) if border else shape
            row += _blend((o, 1.0 - shape), (b, shape - inner), (f, inner))
        rows.append(bytes(row))
    return rows


def rounded_rows(w, h, r, fill, outer, border=None, bw=1):
    """Скруглённый прямоугольник w x h. Считаются только уголки, остальное - копированием."""
    r = max(1, min(r, w // 2, h // 2))
    tl = corner_rows(r, fill, outer, border, bw)
    F = bytes(_rgb(fill))
    B = bytes(_rgb(border)) if border else F
    mid = w - 2 * r
    rows = []
    for y in range(h):
        if y < r or y >= h - r:
            c = tl[y] if y < r else tl[h - 1 - y]
            edge = y < bw or y >= h - bw
            rows.append(c + (B if (border and edge) else F) * mid + _flip(c))
        elif border:
            rows.append(B * bw + F * (w - 2 * bw) + B * bw)
        else:
            rows.append(F * w)
    return rows


def toggle_rows(w, h, pos, track, knob, outer):
    """Переключатель: дорожка-«таблетка» и круглая ручка; pos 0 (слева) .. 1 (справа)."""
    t, k, o = _rgb(track), _rgb(knob), _rgb(outer)
    r = h / 2.0
    kr = r - max(2.0, h * 0.12)
    kx, ky = r + pos * (w - 2 * r), r
    rows = []
    for y in range(h):
        row = bytearray()
        py = y + 0.5
        for x in range(w):
            px = x + 0.5
            qx = abs(px - w / 2.0) - (w / 2.0 - r)
            qy = abs(py - h / 2.0) - (h / 2.0 - r)
            d = math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - r
            a = _clamp(0.5 - d)
            ak = _clamp(0.5 - (math.hypot(px - kx, py - ky) - kr))
            base = _blend((o, 1.0 - a), (t, a))
            row += _blend((base, 1.0 - ak), (k, ak))
        rows.append(bytes(row))
    return rows


class Painter:
    """Создаёт картинки Tk и держит их в кэше (иначе Tk их «забудет»)."""

    def __init__(self, root):
        self.root = root
        self.cache = {}

    def _photo(self, key, w, h, make_rows):
        img = self.cache.get(key)
        if img is None:
            data = base64.b64encode(png_bytes(w, h, make_rows())).decode("ascii")
            img = tk.PhotoImage(master=self.root, data=data, format="png")
            self.cache[key] = img
        return img

    def rounded(self, w, h, r, fill, outer, border=None):
        return self._photo(("rr", w, h, r, fill, outer, border), w, h,
                           lambda: rounded_rows(w, h, r, fill, outer, border))

    def corners(self, r, fill, outer, border=None):
        """Четыре уголка: левый верхний, правый верхний, левый нижний, правый нижний."""
        key = ("corner", r, fill, outer, border)
        if key not in self.cache:
            tl = corner_rows(r, fill, outer, border)
            variants = {
                "tl": tl,
                "tr": [_flip(row) for row in tl],
                "bl": tl[::-1],
                "br": [_flip(row) for row in tl[::-1]],
            }
            self.cache[key] = tuple(
                self._photo(key + (name,), r, r, lambda rows=rows: rows) for name, rows in variants.items())
        return self.cache[key]

    def toggle(self, w, h, on, track, knob, outer):
        return self._photo(("tg", w, h, on, track, knob, outer), w, h,
                           lambda: toggle_rows(w, h, 1.0 if on else 0.0, track, knob, outer))


# =====================================================================
#  Виджеты
# =====================================================================

class RoundedFrame(tk.Frame):
    """Frame со скруглёнными углами и (необязательно) тонкой рамкой.

    Прямые края рисует сам Frame (highlightthickness=1), а в углы кладутся
    картинки-уголки через place(), поверх содержимого. Поэтому внутри можно
    как обычно пользоваться pack/grid - нужен лишь небольшой отступ от краёв.
    """

    def __init__(self, master, painter, fill, border=None, radius=10, outer=None):
        super().__init__(master, bd=0)
        self._painter = painter
        self._radius = radius
        self._style = {"fill": fill, "border": border, "outer": outer or master.cget("bg")}
        self._corners = []
        for anchor, relx, rely in (("nw", 0, 0), ("ne", 1, 0), ("sw", 0, 1), ("se", 1, 1)):
            lbl = tk.Label(self, bd=0, padx=0, pady=0, highlightthickness=0)
            lbl.place(relx=relx, rely=rely, anchor=anchor, bordermode="outside")
            self._corners.append(lbl)
        self.restyle()
        # уголки должны лежать поверх всего, что добавят внутрь позже
        self.after_idle(self.lift_corners)

    @property
    def fill(self):
        return self._style["fill"]

    def lift_corners(self):
        for c in self._corners:
            try:
                c.lift()
            except tk.TclError:
                pass

    def restyle(self, **style):
        """Поменять цвета: restyle(fill=..., border=..., outer=...)."""
        self._style.update(style)
        fill, border, outer = self._style["fill"], self._style["border"], self._style["outer"]
        self.configure(bg=fill, highlightthickness=1 if border else 0,
                       highlightbackground=border or fill, highlightcolor=border or fill)
        for lbl, img in zip(self._corners, self._painter.corners(self._radius, fill, outer, border)):
            lbl.configure(image=img, bg=outer)


class RoundButton(tk.Label):
    """Скруглённая кнопка: картинка-подложка + текст поверх (compound="center")."""

    def __init__(self, master, painter, text, command=None, colors=("#EEEEEE", "#DDDDDD", "#000000"),
                 font=None, padx=14, pady=7, radius=8, disabled_fg="#999999"):
        self._outer = master.cget("bg")
        super().__init__(master, text=text, compound="center", bd=0, padx=0, pady=0,
                         highlightthickness=0, cursor="hand2", bg=self._outer, font=font)
        self._painter = painter
        self._font = tkfont.Font(root=self, font=self.cget("font"))
        self._pad = (padx, pady)
        self._radius = radius
        self._colors = colors
        self._disabled_fg = disabled_fg
        self._hover = False
        self.command = command
        self.enabled = True
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_click)
        self._render()

    def _render(self):
        bg, hover, fg = self._colors
        text = self.cget("text")
        w = self._font.measure(text) + 2 * self._pad[0]
        h = self._font.metrics("linespace") + 2 * self._pad[1]
        fill = hover if (self._hover and self.enabled) else bg
        img = self._painter.rounded(w, h, self._radius, fill, self._outer)
        self.configure(image=img, fg=fg if self.enabled else self._disabled_fg,
                       cursor="hand2" if self.enabled else "arrow")

    def _on_enter(self, _e):
        self._hover = True
        self._render()

    def _on_leave(self, _e):
        self._hover = False
        self._render()

    def _on_click(self, e):
        # срабатываем, только если кнопку отпустили над ней же
        inside = 0 <= e.x < self.winfo_width() and 0 <= e.y < self.winfo_height()
        if inside and self.enabled and self.command:
            self.command()

    def set_text(self, text):
        self.configure(text=text)
        self._render()

    def set_colors(self, colors):
        self._colors = colors
        self._render()

    def set_enabled(self, on):
        self.enabled = bool(on)
        self._render()


class Toggle(tk.Frame):
    """Переключатель с подписью, привязанный к tk.BooleanVar."""

    def __init__(self, master, painter, text, variable, font=None, size=(34, 20),
                 colors=("#0D9488", "#C9D2D5", "#FFFFFF", "#1C2629")):
        bg = master.cget("bg")
        super().__init__(master, bg=bg, cursor="hand2")
        self._painter = painter
        self._size = size
        self._colors = colors              # дорожка вкл, дорожка выкл, ручка, текст
        self._outer = bg
        self.var = variable
        self.switch = tk.Label(self, bd=0, padx=0, pady=0, highlightthickness=0, bg=bg, cursor="hand2")
        self.switch.pack(side="left")
        self.label = tk.Label(self, text=text, font=font, bg=bg, fg=colors[3], cursor="hand2")
        self.label.pack(side="left", padx=(8, 0))
        for w in (self, self.switch, self.label):
            w.bind("<ButtonRelease-1>", self._flip)
        variable.trace_add("write", lambda *_: self._render())
        self._render()

    def _flip(self, _e=None):
        self.var.set(not self.var.get())

    def _render(self):
        on = bool(self.var.get())
        track_on, track_off, knob, _fg = self._colors
        w, h = self._size
        self.switch.configure(image=self._painter.toggle(w, h, on, track_on if on else track_off, knob, self._outer))


class ScrollBar(tk.Canvas):
    """Тонкая полоса прокрутки со скруглённым ползунком.

    Подключается как обычная: widget.configure(yscrollcommand=bar.set), bar.command = widget.yview.
    Когда всё содержимое видно, ползунок скрывается.
    """

    def __init__(self, master, orient="vertical", command=None, colors=("#C5CED1", "#93A1A6"),
                 thickness=10, bg=None):
        self.vertical = orient == "vertical"
        bg = bg or master.cget("bg")
        width, height = (thickness, 1) if self.vertical else (1, thickness)
        super().__init__(master, bg=bg, highlightthickness=0, bd=0, width=width, height=height)
        self.command = command
        self._colors = colors
        self._thick = thickness
        self._first, self._last = 0.0, 1.0
        self._hover = False
        self._drag = None
        self._span = (0.0, 0.0)
        self._thumb = self.create_line(0, 0, 0, 0, capstyle="round", fill=colors[0], state="hidden")
        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._motion)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag", None))
        self.bind("<MouseWheel>", self._wheel)
        self.bind("<Button-4>", lambda e: self._scroll(-1, "units"))
        self.bind("<Button-5>", lambda e: self._scroll(1, "units"))

    # --- интерфейс, который ждут Text/Listbox/Treeview
    def set(self, first, last):
        self._first, self._last = float(first), float(last)
        self._redraw()

    def get(self):
        return self._first, self._last

    # --- отрисовка
    def _length(self):
        return self.winfo_height() if self.vertical else self.winfo_width()

    def _geometry(self):
        width = (self._thick * 0.8) if (self._hover or self._drag) else (self._thick * 0.5)
        pad = width / 2.0 + 2
        usable = max(1.0, self._length() - 2 * pad)
        a = pad + self._first * usable
        b = pad + self._last * usable
        min_len = 24
        if b - a < min_len:                      # слишком короткий ползунок - удлиняем
            extra = min_len - (b - a)
            a = max(pad, a - extra * self._first)
            b = min(pad + usable, a + min_len)
        return width, a, b, usable

    def _redraw(self):
        if self._last - self._first >= 0.999 or self._length() < 20:
            self.itemconfigure(self._thumb, state="hidden")
            return
        width, a, b, _u = self._geometry()
        self._span = (a, b)
        mid = (self.winfo_width() if self.vertical else self.winfo_height()) / 2.0
        coords = (mid, a, mid, b) if self.vertical else (a, mid, b, mid)
        self.coords(self._thumb, *coords)
        color = self._colors[1] if (self._hover or self._drag) else self._colors[0]
        self.itemconfigure(self._thumb, width=width, fill=color, state="normal")

    def _set_hover(self, on):
        self._hover = on
        self._redraw()

    # --- мышь
    def _scroll(self, n, what):
        if self.command:
            self.command("scroll", n, what)

    def _press(self, e):
        pos = e.y if self.vertical else e.x
        a, b = self._span
        if a - 4 <= pos <= b + 4:
            self._drag = (pos, self._first)
        else:
            self._scroll(1 if pos > b else -1, "pages")

    def _motion(self, e):
        if not self._drag or not self.command:
            return
        pos = e.y if self.vertical else e.x
        start, first = self._drag
        usable = self._geometry()[3]
        self.command("moveto", first + (pos - start) / usable)

    def _wheel(self, e):
        step = -1 if e.delta > 0 else 1
        if abs(e.delta) >= 120:
            step *= max(1, abs(e.delta) // 120)
        self._scroll(step, "units")
