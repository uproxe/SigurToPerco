"""Окно программы (tkinter). Работает на Windows, Linux и macOS.

Две вкладки:
  «Номер пропуска»     - один номер или список, пересчёт на лету;
  «Выгрузка из Sigur»  - файл сотрудников -> таблица импорта PERCo.

Вся логика пересчёта - в core.py, современные элементы интерфейса - в widgets.py,
здесь только сборка окна.
"""

import os
import subprocess
import sys
from types import SimpleNamespace

from . import APP_ID, APP_NAME, __version__, core

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# --- палитра (бирюзовый акцент, как на значке)
C = {
    "bg": "#F2F5F6", "card": "#FFFFFF", "border": "#E0E6E8", "text": "#1C2629",
    "muted": "#66757A", "faint": "#9AA7AB", "field": "#F7FAFA",
    "header": "#0F2B30", "header_text": "#FFFFFF", "header_muted": "#9FBDBF",
    "accent": "#0D9488", "accent_hover": "#0F766E", "accent_soft": "#E6F6F4", "accent_line": "#B5E3DD",
    "ok": "#12A150", "ok_soft": "#E6F6EC", "warn": "#C77700", "warn_soft": "#FFF4E0",
    "err": "#D93636",
    "sec": "#EDF1F2", "sec_hover": "#DFE6E8",
    "scroll": "#C9D2D5", "scroll_hover": "#93A1A6", "toggle_off": "#C9D2D5",
}

# Коды клавиш A, C, V, X, Z, Y: нужны, чтобы Ctrl+C/V работали в русской раскладке
_KEYCODES = {
    "win32": {"a": 65, "c": 67, "v": 86, "x": 88, "z": 90, "y": 89},
    "linux": {"a": 38, "c": 54, "v": 55, "x": 53, "z": 52, "y": 29},
}


def assets_dir():
    """Папка assets рядом с программой (или внутри собранного приложения)."""
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "assets")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def asset(*parts):
    return os.path.join(assets_dir(), *parts)


def open_path(path):
    """Открыть файл/папку средствами системы."""
    if IS_WIN:
        os.startfile(path)                                     # type: ignore[attr-defined]
    elif IS_MAC:
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def reveal_in_folder(path):
    """Показать файл в Проводнике / Finder / файловом менеджере."""
    path = os.path.abspath(path)
    if IS_WIN:
        subprocess.Popen('explorer /select,"%s"' % path)
    elif IS_MAC:
        subprocess.Popen(["open", "-R", path])
    else:
        subprocess.Popen(["xdg-open", os.path.dirname(path)])


def _make_root(tk):
    """Главное окно; с поддержкой перетаскивания файлов, если есть tkinterdnd2."""
    try:
        import tkinterdnd2
    except Exception:
        return tk.Tk(className=APP_ID), None
    try:
        return tkinterdnd2.TkinterDnD.Tk(className=APP_ID), tkinterdnd2
    except Exception:
        # окно уже создано, а библиотека tkdnd не загрузилась - закрываем и работаем без неё
        stray = getattr(tk, "_default_root", None)
        if stray is not None:
            try:
                stray.destroy()
            except Exception:
                pass
        return tk.Tk(className=APP_ID), None


def _set_window_icon(tk, root):
    try:
        if IS_WIN:
            root.iconbitmap(default=asset("icon.ico"))
        else:
            imgs = [tk.PhotoImage(master=root, file=asset("icons", "%d.png" % s)) for s in (256, 64, 32)]
            root.iconphoto(True, *imgs)
            root._app_icons = imgs              # держим ссылки, иначе картинки пропадут
    except Exception:
        pass


def run_gui(initial_file=None, on_ready=None):
    """Открыть окно. on_ready(api) - для автоматических проверок (scripts/screenshots.py)."""
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import filedialog, messagebox, ttk

    from .widgets import Painter, RoundButton, RoundedFrame, ScrollBar, Toggle

    if IS_WIN:
        try:                                    # чёткий текст при масштабе 125-150 %
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()    # Windows 7
        except Exception:
            pass
        try:                                    # свой значок на панели задач
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass

    root, dnd = _make_root(tk)
    root.title(APP_NAME)
    root.configure(bg=C["bg"])
    _set_window_icon(tk, root)
    P = Painter(root)

    # --- размеры с учётом масштаба экрана
    scale = max(1.0, root.winfo_fpixels("1i") / 96.0)

    def R(px):
        return int(round(px * scale))

    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    W, H = min(R(1100), sw - 40), min(R(760), sh - 80)
    root.geometry("%dx%d+%d+%d" % (W, H, max(0, (sw - W) // 2), max(0, (sh - H) // 3)))
    root.minsize(min(R(920), sw - 40), min(R(640), sh - 80))

    # --- шрифты под каждую систему
    families = set(tkfont.families(root))

    def pick(cands, fallback):
        for c in cands:
            if c in families:
                return c
        return tkfont.nametofont(fallback).actual("family")

    if IS_WIN:
        UI = pick(["Segoe UI Variable Text", "Segoe UI"], "TkDefaultFont")
        UI_SB = next((f for f in ("Segoe UI Variable Text Semibold", "Segoe UI Semibold") if f in families), None)
        MONO = pick(["Cascadia Mono", "Consolas", "Courier New"], "TkFixedFont")
    elif IS_MAC:
        UI = pick(["SF Pro Text", "Helvetica Neue", ".AppleSystemUIFont"], "TkDefaultFont")
        UI_SB = None
        MONO = pick(["SF Mono", "Menlo", "Monaco"], "TkFixedFont")
    else:
        UI = pick(["Ubuntu", "Noto Sans", "Cantarell", "DejaVu Sans", "Liberation Sans"], "TkDefaultFont")
        UI_SB = None
        MONO = pick(["Ubuntu Mono", "DejaVu Sans Mono", "Noto Sans Mono", "Liberation Mono"], "TkFixedFont")
    FS = 1.3 if IS_MAC else 1.0         # на macOS 1 pt = 1 px, шрифты кажутся мельче

    def fnt(size, bold=False, mono=False):
        s = int(round(size * FS))
        if mono:
            return (MONO, s, "bold") if bold else (MONO, s)
        if bold:
            return (UI_SB, s) if UI_SB else (UI, s, "bold")
        return (UI, s)

    F = {
        "title": fnt(15, True), "subtitle": fnt(9), "tab": fnt(10, True), "h": fnt(12, True),
        "body": fnt(10), "small": fnt(9), "caption": fnt(8, True), "btn": fnt(10, True),
        "btn_big": fnt(11, True), "input": fnt(18, mono=True), "result": fnt(34, True),
        "mono": fnt(10, mono=True), "stat": fnt(20, True), "icon": fnt(20, True),
    }

    # --- таблица предпросмотра: плоский стиль без рамок и «объёмных» заголовков
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    row_h = tkfont.Font(root=root, font=F["body"]).metrics("linespace") + R(12)
    flat = {"bordercolor": C["card"], "lightcolor": C["card"], "darkcolor": C["card"]}
    style.layout("Flat.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure("Flat.Treeview", background=C["card"], fieldbackground=C["card"], foreground=C["text"],
                    rowheight=row_h, font=F["body"], borderwidth=0, relief="flat", **flat)
    style.configure("Flat.Treeview.Heading", background=C["card"], foreground=C["muted"], font=fnt(9, True),
                    relief="flat", borderwidth=0, padding=(R(10), R(8)), **flat)
    style.map("Flat.Treeview", background=[("selected", C["accent_soft"])], foreground=[("selected", C["text"])])
    style.map("Flat.Treeview.Heading", background=[("active", C["sec"]), ("pressed", C["sec"])],
              relief=[("active", "flat"), ("pressed", "flat")])
    try:                                # без пунктирной рамки фокуса у строк
        style.layout("Flat.Treeview.Item", [("Treeitem.padding", {"sticky": "nswe", "children": [
            ("Treeitem.indicator", {"side": "left", "sticky": ""}),
            ("Treeitem.image", {"side": "left", "sticky": ""}),
            ("Treeitem.text", {"side": "left", "sticky": ""})]})])
    except tk.TclError:
        pass

    # ------------------------------------------------------------------
    #  Общие элементы
    # ------------------------------------------------------------------

    KINDS = {
        "primary":   (C["accent"], C["accent_hover"], "#FFFFFF"),
        "secondary": (C["sec"], C["sec_hover"], C["text"]),
        "ghost":     (C["card"], C["sec"], C["accent"]),
    }

    def button(master, text, command=None, kind="secondary", big=False):
        return RoundButton(master, P, text, command, colors=KINDS[kind], font=F["btn_big"] if big else F["btn"],
                           padx=R(20 if big else 14), pady=R(10 if big else 7), radius=R(8),
                           disabled_fg=C["faint"])

    def toggle(master, text, var, font):
        return Toggle(master, P, text, var, font=font, size=(R(34), R(20)),
                      colors=(C["accent"], C["toggle_off"], "#FFFFFF", C["text"]))

    def scrollbar(master, orient, command, bg):
        return ScrollBar(master, orient, command, colors=(C["scroll"], C["scroll_hover"]),
                         thickness=R(10), bg=bg)

    def card(master, title=None, hint=None):
        outer = RoundedFrame(master, P, C["card"], border=C["border"], radius=R(12))
        inner = tk.Frame(outer, bg=C["card"])
        inner.pack(fill="both", expand=True, padx=R(18), pady=R(16))
        if title:
            tk.Label(inner, text=title, font=F["h"], bg=C["card"], fg=C["text"]).pack(anchor="w")
        if hint:
            tk.Label(inner, text=hint, font=F["small"], bg=C["card"], fg=C["muted"],
                     justify="left").pack(anchor="w", pady=(R(2), 0))
        return outer, inner

    def focus_border(box, widget, error_state=None):
        """Рамка поля подсвечивается, когда в нём курсор."""
        def update(focused):
            if error_state and error_state.get("on"):
                box.restyle(border=C["err"])
            else:
                box.restyle(border=C["accent"] if focused else C["border"])
        widget.bind("<FocusIn>", lambda e: update(True), add="+")
        widget.bind("<FocusOut>", lambda e: update(False), add="+")
        return update

    def field(master, var, font=None, pady=6, error_state=None):
        """Поле ввода со скруглённой рамкой. Возвращает (рамка, поле, обновить_рамку)."""
        box = RoundedFrame(master, P, C["field"], border=C["border"], radius=R(8))
        e = tk.Entry(box, textvariable=var, font=font or F["body"], relief="flat", bd=0, highlightthickness=0,
                     bg=C["field"], fg=C["text"], insertbackground=C["text"],
                     selectbackground=C["accent"], selectforeground="#FFFFFF")
        e.pack(fill="x", padx=R(10), pady=R(pady))
        return box, e, focus_border(box, e, error_state)

    def textbox(master, height=6, readonly=False):
        box = RoundedFrame(master, P, C["field"], border=C["border"], radius=R(8))
        t = tk.Text(box, height=height, font=F["mono"], relief="flat", bd=0, highlightthickness=0,
                    bg=C["field"], fg=C["text"], insertbackground=C["text"], wrap="none", undo=True,
                    selectbackground=C["accent"], selectforeground="#FFFFFF", padx=R(6), pady=R(4))
        sb = scrollbar(box, "vertical", t.yview, C["field"])
        t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(0, R(3)), pady=R(5))
        t.pack(side="left", fill="both", expand=True, padx=(R(6), 0), pady=R(5))
        focus_border(box, t)
        if readonly:
            # печатать нельзя, но выделять и копировать можно
            t.bind("<Key>", lambda e: None if (int(e.state) & 0x4) or (IS_MAC and int(e.state) & 0x8) else "break")
            for ev in ("<<Paste>>", "<<Cut>>", "<<Undo>>", "<<Redo>>"):
                t.bind(ev, lambda e: "break")
        return box, t

    def copy_to_clipboard(s):
        root.clipboard_clear()
        root.clipboard_append(s)
        root.update_idletasks()

    def select_all(w):
        if isinstance(w, tk.Entry):
            w.select_range(0, "end")
            w.icursor("end")
        elif isinstance(w, tk.Text):
            w.tag_add("sel", "1.0", "end-1c")

    # --- Ctrl+A/C/V/X/Z/Y в любой раскладке (в русской Tk не узнаёт эти сочетания)
    codes = _KEYCODES.get("win32" if IS_WIN else ("linux" if IS_LINUX else ""), {})

    def on_ctrl_key(event):
        w = event.widget
        if not isinstance(w, (tk.Entry, tk.Text)) or not codes:
            return None
        kc = event.keycode
        if kc == codes["a"]:
            select_all(w)
            return "break"
        if event.keysym.lower() in ("a", "c", "v", "x", "z", "y"):
            return None                                     # латиница - Tk справится сам
        action = {codes["c"]: "<<Copy>>", codes["v"]: "<<Paste>>", codes["x"]: "<<Cut>>",
                  codes["z"]: "<<Undo>>", codes["y"]: "<<Redo>>"}.get(kc)
        if action:
            w.event_generate(action)
            return "break"
        return None

    if codes:
        root.bind_all("<Control-KeyPress>", on_ctrl_key, add="+")

    # --- меню по правой кнопке мыши
    ctx = tk.Menu(root, tearoff=0)

    def show_ctx(event):
        w = event.widget
        w.focus_set()
        ctx.delete(0, "end")
        ctx.add_command(label="Вырезать", command=lambda: w.event_generate("<<Cut>>"))
        ctx.add_command(label="Копировать", command=lambda: w.event_generate("<<Copy>>"))
        ctx.add_command(label="Вставить", command=lambda: w.event_generate("<<Paste>>"))
        ctx.add_separator()
        ctx.add_command(label="Выделить всё", command=lambda: select_all(w))
        ctx.tk_popup(event.x_root, event.y_root)

    for cls in ("Entry", "Text"):
        for ev in (("<Button-2>", "<Control-Button-1>") if IS_MAC else ("<Button-3>",)):
            root.bind_class(cls, ev, show_ctx, add="+")

    # ------------------------------------------------------------------
    #  Шапка, вкладки, строка состояния
    # ------------------------------------------------------------------

    header = tk.Frame(root, bg=C["header"])
    header.pack(fill="x")
    hin = tk.Frame(header, bg=C["header"])
    hin.pack(fill="x", padx=R(22), pady=(R(14), 0))

    logo = None
    for name in (("64.png", "48.png") if scale >= 1.4 else ("48.png",)):
        try:
            logo = tk.PhotoImage(master=root, file=asset("icons", name))
            break
        except Exception:
            logo = None
    if logo is not None:
        tk.Label(hin, image=logo, bg=C["header"]).pack(side="left", padx=(0, R(12)))
        root._app_logo = logo                 # держим ссылку, иначе картинка пропадёт

    tbox = tk.Frame(hin, bg=C["header"])
    tbox.pack(side="left")
    tk.Label(tbox, text=APP_NAME, font=F["title"], bg=C["header"], fg=C["header_text"]).pack(anchor="w")
    tk.Label(tbox, text="Пересчёт номеров пропусков и подготовка выгрузки сотрудников для импорта в PERCo",
             font=F["subtitle"], bg=C["header"], fg=C["header_muted"]).pack(anchor="w")
    tk.Label(hin, text="v" + __version__, font=F["small"], bg=C["header"],
             fg=C["header_muted"]).pack(side="right", anchor="n")

    tabs_bar = tk.Frame(header, bg=C["header"])
    tabs_bar.pack(fill="x", padx=R(14), pady=(R(12), 0))

    body = tk.Frame(root, bg=C["bg"])
    body.pack(fill="both", expand=True, padx=R(18), pady=(R(16), 0))

    status = tk.Frame(root, bg=C["bg"])
    status.pack(fill="x", padx=R(20), pady=(R(8), R(10)))
    status_lbl = tk.Label(status, text="", font=F["small"], bg=C["bg"], fg=C["muted"], anchor="w")
    status_lbl.pack(side="left", fill="x", expand=True)
    hint = ("⌘V — вставить и сразу скопировать результат  •  Enter — скопировать ещё раз" if IS_MAC else
            "Ctrl+V работает в любой раскладке  •  Enter — конвертировать и скопировать")
    tk.Label(status, text=hint, font=F["small"], bg=C["bg"], fg=C["faint"]).pack(side="right")

    status_job = {"id": ""}

    def toast(msg, kind="ok"):
        colors = {"ok": C["ok"], "warn": C["warn"], "err": C["err"], "info": C["muted"]}
        icon = {"ok": "✔  ", "warn": "⚠  ", "err": "✖  ", "info": ""}[kind]
        status_lbl.configure(text=icon + msg, fg=colors[kind])
        if status_job["id"]:
            root.after_cancel(status_job["id"])
        status_job["id"] = root.after(6000, lambda: status_lbl.configure(text=""))

    pages, tab_btns = {}, {}

    def show_tab(name):
        for p in pages.values():
            p.pack_forget()
        pages[name].pack(fill="both", expand=True)
        for n, (lbl, line) in tab_btns.items():
            on = n == name
            lbl.configure(fg="#FFFFFF" if on else C["header_muted"])
            line.configure(bg=C["accent"] if on else C["header"])
        if name == "card":
            card_entry.focus_set()

    def make_tab(name, label):
        fr = tk.Frame(tabs_bar, bg=C["header"], cursor="hand2")
        fr.pack(side="left", padx=(R(8), R(18)))
        lbl = tk.Label(fr, text=label, font=F["tab"], bg=C["header"], fg=C["header_muted"], pady=R(6))
        lbl.pack()
        line = tk.Frame(fr, height=R(3), bg=C["header"])
        line.pack(fill="x")
        for w in (fr, lbl):
            w.bind("<Button-1>", lambda e, n=name: show_tab(n))
        lbl.bind("<Enter>", lambda e, lb=lbl: lb.configure(fg="#FFFFFF"))
        lbl.bind("<Leave>", lambda e, lb=lbl, n=name: lb.configure(
            fg="#FFFFFF" if pages[n].winfo_ismapped() else C["header_muted"]))
        tab_btns[name] = (lbl, line)

    make_tab("card", "Номер пропуска")
    make_tab("file", "Выгрузка из Sigur")

    # ------------------------------------------------------------------
    #  Вкладка «Номер пропуска»
    # ------------------------------------------------------------------

    pg_card = tk.Frame(body, bg=C["bg"])
    pages["card"] = pg_card
    pg_card.columnconfigure(0, weight=5, uniform="c")
    pg_card.columnconfigure(1, weight=4, uniform="c")
    pg_card.rowconfigure(0, weight=1)

    left_o, left = card(pg_card, "Один пропуск",
                        "Вставьте номер из Sigur (например 000000AB12CD34) — результат посчитается сразу.\n"
                        "Можно и наоборот: введите номер PERCo (18/52532) — получите HEX для Sigur.")
    left_o.grid(row=0, column=0, sticky="nsew", padx=(0, R(8)))

    card_var = tk.StringVar(master=root)
    card_error = {"on": False}
    card_box, card_entry, card_focus = field(left, card_var, font=F["input"], pady=9, error_state=card_error)
    card_box.pack(fill="x", pady=(R(14), 0))

    res_box = RoundedFrame(left, P, C["accent_soft"], radius=R(10))
    res_box.pack(fill="x", pady=(R(12), 0))
    res_cap = tk.Label(res_box, text="НОМЕР ДЛЯ PERCO", font=F["caption"], bg=C["accent_soft"], fg=C["accent"])
    res_cap.pack(anchor="w", padx=R(16), pady=(R(12), 0))
    res_lbl = tk.Label(res_box, text="—", font=F["result"], bg=C["accent_soft"], fg=C["faint"], cursor="hand2")
    res_lbl.pack(anchor="w", padx=R(14))
    res_detail = tk.Label(res_box, text=" ", font=F["mono"], bg=C["accent_soft"], fg=C["muted"], justify="left")
    res_detail.pack(anchor="w", padx=R(16), pady=(0, R(12)))

    card_btns = tk.Frame(left, bg=C["card"])
    card_btns.pack(fill="x", pady=(R(12), 0))

    hist_head = tk.Frame(left, bg=C["card"])
    hist_head.pack(fill="x", pady=(R(18), R(6)))
    tk.Label(hist_head, text="История", font=fnt(10, True), bg=C["card"], fg=C["text"]).pack(side="left")
    tk.Label(hist_head, text="двойной щелчок — скопировать", font=F["small"], bg=C["card"],
             fg=C["faint"]).pack(side="left", padx=R(8))

    hist_box = RoundedFrame(left, P, C["field"], border=C["border"], radius=R(8))
    hist_box.pack(fill="both", expand=True)
    hist = tk.Listbox(hist_box, font=F["mono"], relief="flat", borderwidth=0, bg=C["field"], fg=C["text"],
                      activestyle="none", selectbackground=C["accent_soft"], selectforeground=C["text"],
                      highlightthickness=0)
    hist_sb = scrollbar(hist_box, "vertical", hist.yview, C["field"])
    hist.configure(yscrollcommand=hist_sb.set)
    hist_sb.pack(side="right", fill="y", padx=(0, R(3)), pady=R(5))
    hist.pack(side="left", fill="both", expand=True, padx=(R(8), 0), pady=R(5))
    history = []                        # [(ввод, результат)]

    current = {"out": "", "inp": ""}

    def compute(value):
        """-> (результат, пояснение, подпись, текст ошибки)"""
        v = value.strip()
        if not v:
            return "", "", "НОМЕР ДЛЯ PERCO", ""
        if "/" in v or "\\" in v:
            try:
                return core.perco_to_sigur(v), "последние 6 знаков номера в Sigur (W58)", "HEX ДЛЯ SIGUR", ""
            except ValueError as e:
                return "", "", "HEX ДЛЯ SIGUR", str(e)
        try:
            r = core.sigur_card(v)
        except ValueError as e:
            return "", "", "НОМЕР ДЛЯ PERCO", str(e)
        detail = "%s  →  %s = %d  ·  %s = %d" % (r.hex6, r.hex6[:2], r.series, r.hex6[2:], r.number)
        return r.perco, detail, "НОМЕР ДЛЯ PERCO", ""

    def refresh(*_):
        out, detail, cap, err = compute(card_var.get())
        res_cap.configure(text=cap)
        current["out"], current["inp"] = out, card_var.get().strip()
        if err:
            res_lbl.configure(text="—", fg=C["faint"])
            res_detail.configure(text=err, fg=C["err"])
        else:
            res_lbl.configure(text=out or "—", fg=C["text"] if out else C["faint"])
            res_detail.configure(text=detail or " ", fg=C["muted"])
        if card_error["on"] != bool(err):
            card_error["on"] = bool(err)
            try:
                focused = root.focus_get() is card_entry
            except (KeyError, tk.TclError):
                focused = False
            card_focus(focused)

    def add_history(inp, out):
        if history and history[0] == (inp, out):
            return
        history.insert(0, (inp, out))
        del history[200:]
        hist.delete(0, "end")
        for i, o in history:
            hist.insert("end", "%-20s →  %s" % (i, o))

    def copy_current(*_):
        refresh()
        if not current["out"]:
            toast("Нечего копировать — введите номер.", "warn")
            return "break"
        copy_to_clipboard(current["out"])
        add_history(current["inp"], current["out"])
        toast("Скопировано в буфер: " + current["out"])
        return "break"

    def set_card_text(s):
        s = (s or "").strip()
        card_var.set(s.splitlines()[0].strip() if s else "")
        card_entry.icursor("end")

    def paste_convert():
        try:
            s = root.clipboard_get()
        except tk.TclError:
            toast("Буфер обмена пуст.", "warn")
            return
        set_card_text(s)
        copy_current()

    def clear_card():
        card_var.set("")
        card_entry.focus_set()

    def after_paste():
        refresh()
        if current["out"]:
            copy_current()

    def on_entry_paste(_e):
        # вставка заменяет всё поле, а результат сразу попадает в буфер
        try:
            s = root.clipboard_get()
        except tk.TclError:
            return "break"
        set_card_text(s)
        root.after(10, after_paste)
        return "break"

    card_var.trace_add("write", refresh)
    card_entry.bind("<Return>", copy_current)
    card_entry.bind("<KP_Enter>", copy_current)
    card_entry.bind("<<Paste>>", on_entry_paste)
    res_lbl.bind("<Button-1>", copy_current)

    button(card_btns, "Скопировать результат", copy_current, kind="primary").pack(side="left")
    button(card_btns, "Вставить из буфера", paste_convert).pack(side="left", padx=R(8))
    button(card_btns, "Очистить", clear_card, kind="ghost").pack(side="left")

    def hist_copy(_e=None):
        sel = hist.curselection()
        if sel:
            out = history[sel[0]][1]
            copy_to_clipboard(out)
            toast("Скопировано в буфер: " + out)

    hist.bind("<Double-Button-1>", hist_copy)
    hist.bind("<Return>", hist_copy)

    # --- правая колонка: список
    right_o, right = card(pg_card, "Список пропусков",
                          "По одному номеру в строке. Результат копируется в две колонки — удобно вставлять в Excel.")
    right_o.grid(row=0, column=1, sticky="nsew", padx=(R(8), 0))

    tk.Label(right, text="Номера из Sigur (или PERCo)", font=F["small"], bg=C["card"],
             fg=C["muted"]).pack(anchor="w", pady=(R(12), R(4)))
    batch_in_box, batch_in = textbox(right, height=7)
    batch_in_box.pack(fill="both", expand=True)

    bopts = tk.Frame(right, bg=C["card"])
    bopts.pack(fill="x", pady=(R(10), 0))
    only_res = tk.BooleanVar(master=root, value=False)

    tk.Label(right, text="Результат", font=F["small"], bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(R(10), R(4)))
    batch_out_box, batch_out = textbox(right, height=7, readonly=True)
    batch_out_box.pack(fill="both", expand=True)
    batch_out.tag_configure("err", foreground=C["err"])
    batch_out.tag_configure("dim", foreground=C["faint"])

    batch_lines = []                    # [(ввод, результат)] - для копирования

    def convert_batch():
        lines = [ln.strip() for ln in batch_in.get("1.0", "end").splitlines() if ln.strip()]
        batch_out.delete("1.0", "end")
        del batch_lines[:]
        ok = bad = 0
        for line in lines:
            out, _d, _c, err = compute(line)
            batch_out.insert("end", line, "dim")
            if err:
                bad += 1
                batch_out.insert("end", "\tОШИБКА: %s\n" % err, "err")
                batch_lines.append((line, "ОШИБКА"))
            else:
                ok += 1
                batch_out.insert("end", "\t%s\n" % out)
                batch_lines.append((line, out))
        if not lines:
            toast("Вставьте номера в верхнее поле — по одному в строке.", "warn")
        elif bad:
            toast("Готово: %d номеров, с ошибкой — %d." % (ok, bad), "warn")
        else:
            toast("Готово: %d номеров." % ok)

    def copy_batch():
        if not batch_lines:
            convert_batch()
        if not batch_lines:
            return
        if only_res.get():
            s = "\n".join(o for _i, o in batch_lines)
        else:
            s = "\n".join("%s\t%s" % (i, o) for i, o in batch_lines)
        copy_to_clipboard(s)
        toast("Скопировано строк: %d" % len(batch_lines))

    def clear_batch():
        batch_in.delete("1.0", "end")
        batch_out.delete("1.0", "end")
        del batch_lines[:]

    button(bopts, "Конвертировать", convert_batch, kind="primary").pack(side="left")
    button(bopts, "Копировать", copy_batch).pack(side="left", padx=R(8))
    button(bopts, "Очистить", clear_batch, kind="ghost").pack(side="left")
    toggle(bopts, "только результат", only_res, F["small"]).pack(side="right")

    # ------------------------------------------------------------------
    #  Вкладка «Выгрузка из Sigur»
    # ------------------------------------------------------------------

    pg_file = tk.Frame(body, bg=C["bg"])
    pages["file"] = pg_file

    src_var = tk.StringVar(master=root)
    dst_var = tk.StringVar(master=root)
    until_var = tk.StringVar(master=root, value=core.UNLIMITED_UNTIL)
    upper_var = tk.BooleanVar(master=root, value=core.UPPERCASE_NAMES)
    last_res = {"res": None}

    top = tk.Frame(pg_file, bg=C["bg"])
    top.pack(fill="x")
    top.columnconfigure(0, weight=3, uniform="t")
    top.columnconfigure(1, weight=2, uniform="t")

    f1_o, f1 = card(top, "1. Файл выгрузки сотрудников из Sigur")
    f1_o.grid(row=0, column=0, sticky="nsew", padx=(0, R(8)))

    drop = RoundedFrame(f1, P, C["accent_soft"], border=C["accent_line"], radius=R(10))
    drop.configure(cursor="hand2")
    drop.pack(fill="both", expand=True, pady=(R(12), 0))
    drop_icon = tk.Label(drop, text="⇩", font=F["icon"], bg=C["accent_soft"], fg=C["accent"], cursor="hand2")
    drop_icon.pack(pady=(R(14), 0))
    drop_text = "Перетащите сюда файл выгрузки" if dnd else "Нажмите, чтобы выбрать файл выгрузки"
    drop_main = tk.Label(drop, text=drop_text, font=F["btn_big"], bg=C["accent_soft"], fg=C["text"], cursor="hand2")
    drop_main.pack(padx=R(16))
    drop_sub = tk.Label(drop, text=("или нажмите, чтобы выбрать  •  .xls / .xlsx" if dnd else ".xls / .xlsx"),
                        font=F["small"], bg=C["accent_soft"], fg=C["muted"], cursor="hand2",
                        wraplength=R(520))
    drop_sub.pack(padx=R(16), pady=(R(2), R(14)))

    f2_o, f2 = card(top, "2. Параметры")
    f2_o.grid(row=0, column=1, sticky="nsew", padx=(R(8), 0))
    tk.Label(f2, text="«Действует до» для пропусков без срока", font=F["small"], bg=C["card"],
             fg=C["muted"]).pack(anchor="w", pady=(R(12), R(4)))
    until_box, _until_entry, _ = field(f2, until_var, font=F["mono"])
    until_box.pack(fill="x")
    toggle(f2, "ФИО заглавными буквами", upper_var, F["body"]).pack(anchor="w", pady=(R(12), 0))
    tk.Label(f2, text="Сохранить как", font=F["small"], bg=C["card"],
             fg=C["muted"]).pack(anchor="w", pady=(R(12), R(4)))
    dst_row = tk.Frame(f2, bg=C["card"])
    dst_row.pack(fill="x")
    dst_box, _dst_entry, _ = field(dst_row, dst_var, font=F["small"])
    dst_box.pack(side="left", fill="x", expand=True)

    action = tk.Frame(pg_file, bg=C["bg"])
    action.pack(fill="x", pady=R(12))
    run_btn = button(action, "Конвертировать в PERCo  →", kind="primary", big=True)
    run_btn.pack(side="left")
    open_btn = button(action, "Открыть файл")
    open_btn.pack(side="left", padx=(R(12), 0))
    folder_btn = button(action, "Показать в папке")
    folder_btn.pack(side="left", padx=R(8))
    open_btn.set_enabled(False)
    folder_btn.set_enabled(False)

    # --- результат
    r_o, r = card(pg_file)
    r_o.pack(fill="both", expand=True)

    stats = tk.Frame(r, bg=C["card"])
    stats.pack(fill="x")
    stat_tiles = {}
    for i, (key, cap) in enumerate([("rows", "строк для PERCo"), ("people", "сотрудников"),
                                    ("cards_ok", "пропусков пересчитано"), ("warn", "предупреждений")]):
        stats.columnconfigure(i, weight=1, uniform="s")
        tile = RoundedFrame(stats, P, C["sec"], radius=R(10))
        tile.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else R(8), 0))
        v = tk.Label(tile, text="—", font=F["stat"], bg=C["sec"], fg=C["text"])
        v.pack(anchor="w", padx=R(14), pady=(R(8), 0))
        c = tk.Label(tile, text=cap, font=F["small"], bg=C["sec"], fg=C["muted"])
        c.pack(anchor="w", padx=R(14), pady=(0, R(10)))
        stat_tiles[key] = (tile, v, c)

    seg = tk.Frame(r, bg=C["card"])
    seg.pack(fill="x", pady=(R(14), R(8)))
    view_area = tk.Frame(r, bg=C["card"])
    view_area.pack(fill="both", expand=True)

    # предпросмотр (индекс колонки в таблице PERCo, заголовок, ширина)
    prev_box = RoundedFrame(view_area, P, C["card"], border=C["border"], radius=R(8))
    prev_in = tk.Frame(prev_box, bg=C["card"])
    prev_in.pack(fill="both", expand=True, padx=R(4), pady=R(4))
    prev_cols = [(0, "Фамилия", 120), (1, "Имя", 100), (2, "Отчество", 120), (4, "Таб. №", 70),
                 (6, "Подразделение", 220), (10, "Карта №", 90), (12, "Действует с", 140),
                 (13, "Действует до", 140), (3, "Блок.", 50)]
    tree = ttk.Treeview(prev_in, columns=[str(i) for i in range(len(prev_cols))], show="headings",
                        style="Flat.Treeview")
    for i, (_idx, name, w) in enumerate(prev_cols):
        tree.heading(str(i), text=name, anchor="w")
        tree.column(str(i), width=R(w), minwidth=R(40), anchor="w", stretch=(name == "Подразделение"))
    tvs = scrollbar(prev_in, "vertical", tree.yview, C["card"])
    ths = scrollbar(prev_in, "horizontal", tree.xview, C["card"])
    tree.configure(yscrollcommand=tvs.set, xscrollcommand=ths.set)
    prev_in.rowconfigure(0, weight=1)
    prev_in.columnconfigure(0, weight=1)
    tree.grid(row=0, column=0, sticky="nsew")
    tvs.grid(row=0, column=1, sticky="ns")
    ths.grid(row=1, column=0, sticky="ew")
    tree.tag_configure("odd", background=C["field"])
    tree.tag_configure("nocard", foreground=C["warn"])

    empty_lbl = tk.Label(view_area, text="Здесь появится предпросмотр таблицы для PERCo",
                         font=F["body"], bg=C["card"], fg=C["faint"])

    warn_box, warn_t = textbox(view_area, height=8, readonly=True)
    warn_t.configure(wrap="word", font=F["body"], spacing1=R(2), spacing3=R(2))

    seg_btns = {}

    def show_view(name):
        for w in (prev_box, warn_box, empty_lbl):
            w.pack_forget()
        if last_res["res"] is None:
            empty_lbl.pack(fill="both", expand=True, pady=R(30))
        elif name == "prev":
            prev_box.pack(fill="both", expand=True)
        else:
            warn_box.pack(fill="both", expand=True)
        for n, b in seg_btns.items():
            b.set_colors(KINDS["primary" if n == name else "secondary"])

    seg_btns["prev"] = button(seg, "Предпросмотр", lambda: show_view("prev"))
    seg_btns["prev"].pack(side="left")
    seg_btns["warn"] = button(seg, "Предупреждения", lambda: show_view("warn"))
    seg_btns["warn"].pack(side="left", padx=(R(6), 0))

    def set_src(path):
        path = (path or "").strip().strip("{}").strip('"')
        if not path:
            return
        src_var.set(path)
        dst_var.set(core.default_output_path(path))
        drop_icon.configure(text="✔", fg=C["ok"])
        drop_main.configure(text=os.path.basename(path))
        drop_sub.configure(text=os.path.dirname(path) + ("   •   перетащите другой или нажмите, чтобы сменить"
                                                         if dnd else "   •   нажмите, чтобы сменить"))
        show_tab("file")

    def pick_src(_e=None):
        path = filedialog.askopenfilename(parent=root, title="Выгрузка сотрудников из Sigur",
                                          filetypes=[("Excel", "*.xls *.xlsx"), ("Все файлы", "*")])
        if path:
            set_src(path)
            do_convert()

    def pick_dst():
        cur = dst_var.get().strip()
        path = filedialog.asksaveasfilename(
            parent=root, title="Куда сохранить файл для PERCo", defaultextension=".xlsx",
            initialfile=os.path.basename(cur) if cur else "userPERCO.xlsx",
            initialdir=os.path.dirname(cur) if cur else None, filetypes=[("Excel", "*.xlsx")])
        if path:
            dst_var.set(path)

    button(dst_row, "…", pick_dst).pack(side="left", padx=(R(6), 0))

    for w in (drop, drop_icon, drop_main, drop_sub):
        w.bind("<Button-1>", pick_src)
        w.bind("<Enter>", lambda e: drop.restyle(border=C["accent"]))
        w.bind("<Leave>", lambda e: drop.restyle(border=C["accent_line"]))

    def safe(fn, *a):
        try:
            fn(*a)
        except Exception as e:
            toast("Не удалось открыть: %s" % e, "err")

    open_btn.command = lambda: last_res["res"] and safe(open_path, last_res["res"].out_path)
    folder_btn.command = lambda: last_res["res"] and safe(reveal_in_folder, last_res["res"].out_path)

    def do_convert():
        src = src_var.get().strip()
        if not src:
            pick_src()
            return
        if not os.path.exists(src):
            toast("Файл не найден: " + src, "err")
            return
        root.configure(cursor="watch")
        root.update_idletasks()
        try:
            res = core.convert_file(src, dst_var.get().strip() or None, until=until_var.get().strip(),
                                    upper=upper_var.get())
        except Exception as e:
            root.configure(cursor="")
            toast("Ошибка: %s" % str(e).splitlines()[0], "err")
            messagebox.showerror(APP_NAME, str(e), parent=root)
            return
        root.configure(cursor="")
        last_res["res"] = res
        dst_var.set(res.out_path)

        s = res.stats
        for key, val in (("rows", s["rows"]), ("people", s["people"]), ("cards_ok", s["cards_ok"]),
                         ("warn", len(res.warnings))):
            stat_tiles[key][1].configure(text=str(val))
        tile, vl, cl = stat_tiles["warn"]
        bgc = C["warn_soft"] if res.warnings else C["ok_soft"]
        tile.restyle(fill=bgc)
        for w in (vl, cl):
            w.configure(bg=bgc)
        vl.configure(fg=C["warn"] if res.warnings else C["ok"])

        tree.delete(*tree.get_children())
        for n, rec in enumerate(res.records):
            tags = ["odd"] if n % 2 else []
            if not rec[10]:
                tags.append("nocard")
            tree.insert("", "end", values=[rec[i] for i, _n, _w in prev_cols], tags=tags)

        warn_t.delete("1.0", "end")
        warn_t.insert("1.0", "\n".join("•  " + w for w in res.warnings) if res.warnings
                      else "Предупреждений нет — всё перенеслось без вопросов.")
        seg_btns["warn"].set_text("Предупреждения (%d)" % len(res.warnings))
        show_view("prev")
        open_btn.set_enabled(True)
        folder_btn.set_enabled(True)
        if s["cards_bad"] or s["cards_empty"]:
            toast("Сохранено: %s  (есть строки без карты — см. предупреждения)"
                  % os.path.basename(res.out_path), "warn")
        else:
            toast("Сохранено: %s" % os.path.basename(res.out_path))

    run_btn.command = do_convert

    def open_file_from_system(path):
        set_src(path)
        do_convert()

    # --- перетаскивание файлов
    if dnd is not None:
        def on_drop(event):
            files = root.tk.splitlist(event.data)
            if files:
                open_file_from_system(files[0])
            return getattr(event, "action", "copy")

        for w in (root, drop, drop_main, drop_sub, drop_icon):
            try:
                w.drop_target_register(dnd.DND_FILES)
                w.dnd_bind("<<Drop>>", on_drop)
            except Exception:
                pass

    # --- macOS: файл открыли через Finder («Открыть с помощью» / на значок в Dock)
    if IS_MAC:
        try:
            root.createcommand("::tk::mac::OpenDocument", lambda *paths: paths and open_file_from_system(paths[0]))
        except Exception:
            pass

    show_view("prev")
    show_tab("card")
    toast("Готово к работе.", "info")

    if initial_file:
        root.after(300, lambda: open_file_from_system(initial_file))

    if on_ready is not None:
        api = SimpleNamespace(
            root=root, show_tab=show_tab, show_view=show_view, open_file=open_file_from_system,
            set_card=card_var.set, convert_batch=convert_batch,
            set_batch=lambda s: (batch_in.delete("1.0", "end"), batch_in.insert("1.0", s)),
            copy_current=copy_current, toggle_upper=lambda: upper_var.set(not upper_var.get()),
        )
        root.after(500, lambda: on_ready(api))

    root.mainloop()
