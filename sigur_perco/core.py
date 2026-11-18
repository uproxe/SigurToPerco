"""Логика без интерфейса: пересчёт номеров и конвертация выгрузки.

Модуль можно использовать отдельно от окна программы:

    >>> from sigur_perco import core
    >>> core.sigur_card("000000AB12CD34").perco
    '18/52532'
    >>> core.perco_to_sigur("18/52532")
    '12CD34'

Как пересчитывается номер
-------------------------
Sigur показывает номер карты в HEX (формат W58), PERCo - как «серия/номер»
(классический Wiegand-26: код объекта 0-255 и номер карты 0-65535).

    Sigur:  000000AB12CD34
            последние 6 знаков            -> 12CD34
            серия = HEX->DEC первых 2     -> 12   = 18
            номер = HEX->DEC следующих 4  -> CD34 = 52532
    PERCo:  "серия/номер"                 -> 18/52532
"""

import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser

# =====================================================================
#  НАСТРОЙКИ - при необходимости меняйте здесь
# =====================================================================

# Что писать в «Действует до», если в Sigur срок пропуска «не ограничен».
# (В PERCo это поле не бывает пустым.) В окне программы значение можно поменять.
UNLIMITED_UNTIL = "2032-01-31 23:00:00"

# True - Фамилию, Имя и Отчество писать ЗАГЛАВНЫМИ
UPPERCASE_NAMES = False

# Какие «Тип записи» из Sigur переносить. Пустое множество = переносить все.
ONLY_RECORD_TYPES = {"сотрудник"}

# Что писать во все строки в колонки «Шаблон доступа» и «График работы»
ACCESS_TEMPLATE = ""
WORK_SCHEDULE = ""

# =====================================================================

DT_FMT = "%Y-%m-%d %H:%M:%S"

# Колонки файла импорта сотрудников PERCo-Web - порядок важен
PERCO_HEADERS = [
    "Фамилия", "Имя", "Отчество", "Блокировка", "Табельный номер",
    "Дата приема на работу", "Подразделение", "Должность", "Шаблон доступа",
    "График работы", "Карта №", "Штрих-код", "Действует с", "Действует до",
    "Дата увольнения", "Фото", "Транспортное средство", "Биометрия",
]
COLUMN_WIDTHS = [20, 18, 22, 12, 16, 20, 36, 42, 22, 16, 14, 12, 21, 21, 16, 8, 22, 12]

# Какие заголовки искать в выгрузке Sigur (регистр и лишние пробелы не важны)
COLUMN_ALIASES = {
    "type":    ("тип записи",),
    "fio":     ("имя", "фио"),
    "dept":    ("отдел", "подразделение"),
    "pos":     ("должность/модель", "должность"),
    "tab":     ("таб. №", "таб №", "таб.№", "табельный номер"),
    "mode":    ("режим",),
    "card":    ("номер пропуска",),
    "issued":  ("время выдачи",),
    "expires": ("срок действия",),
}

_DT_FORMATS = (
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
    "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%Y-%m-%d", "%d.%m.%Y",
)
_HEX_RE = re.compile(r"^[0-9A-Fa-f]{6,}$")


# =====================================================================
#  Номер пропуска
# =====================================================================

def clean_hex(value):
    """Строка из Sigur -> только HEX-символы (убираем 'W58', пробелы, двоеточия...)."""
    s = str(value or "").upper().replace("W58", "")
    return re.sub(r"[^0-9A-F]", "", s)


@dataclass
class CardResult:
    hex6: str      # последние 6 HEX-знаков, напр. 12CD34
    series: int    # 18
    number: int    # 52532

    @property
    def perco(self):
        return "%d/%d" % (self.series, self.number)


def sigur_card(value):
    """'000000AB12CD34' -> CardResult('12CD34', 18, 52532). Ошибка -> ValueError."""
    s = clean_hex(value)
    if len(s) < 6:
        raise ValueError("Нужно минимум 6 HEX-символов (0-9, A-F).")
    h = s[-6:]
    return CardResult(h, int(h[:2], 16), int(h[2:], 16))


def perco_to_sigur(value):
    """'18/52532' -> '12CD34' (последние 6 знаков номера в Sigur)."""
    m = re.fullmatch(r"\s*(\d{1,3})\s*[/\\]\s*(\d{1,5})\s*", str(value or ""))
    if not m:
        raise ValueError("Номер PERCo должен быть вида 18/52532.")
    series, number = int(m.group(1)), int(m.group(2))
    if series > 255:
        raise ValueError("Серия (до «/») должна быть от 0 до 255.")
    if number > 65535:
        raise ValueError("Номер (после «/») должен быть от 0 до 65535.")
    return "%02X%04X" % (series, number)


def convert_any(value):
    """Сам понимает направление: '…/…' -> HEX для Sigur, иначе -> номер PERCo."""
    v = str(value or "").strip()
    if "/" in v or "\\" in v:
        return perco_to_sigur(v)
    return sigur_card(v).perco


def sigur_to_perco_card(raw):
    """Для выгрузки: строгая проверка. '000000AB12CD34' -> '18/52532', мусор -> None.
    Допускаются приставка 'W58' и разделители (пробел, ':', '-'), всё остальное - ошибка."""
    s = re.sub(r"^\s*W58\s*:?", "", text(raw), flags=re.I)
    s = re.sub(r"[\s:\-]", "", s)
    if not _HEX_RE.match(s):
        return None
    h = s[-6:]
    return "%d/%d" % (int(h[:2], 16), int(h[2:], 16))


# =====================================================================
#  Мелкие помощники
# =====================================================================

def text(v):
    """Значение ячейки -> аккуратная строка ('' для пустых)."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else str(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, datetime):
        return v.strftime(DT_FMT)
    return str(v).replace("\xa0", " ").strip()


def parse_dt(s):
    """Строка с датой/временем -> datetime или None."""
    s = text(s)
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


# =====================================================================
#  Чтение выгрузки Sigur (.xls, .xlsx или HTML-таблица с расширением .xls)
# =====================================================================

class _HtmlTable(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._row is not None and self._cell is not None:
            self._row.append("".join(self._cell).strip() or None)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def _read_html(raw):
    s = None
    for enc in ("utf-8", "cp1251"):
        try:
            s = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if s is None:
        s = raw.decode("utf-8", "replace")
    p = _HtmlTable()
    p.feed(s)
    return p.rows


def read_table(path):
    """Первый лист файла -> список строк (списков значений)."""
    with open(path, "rb") as f:
        raw = f.read()

    if raw.startswith(b"\xd0\xcf\x11\xe0"):                 # старый .xls (OLE2)
        import xlrd
        book = xlrd.open_workbook(file_contents=raw)
        sheet = book.sheet_by_index(0)
        rows = []
        for r in range(sheet.nrows):
            row = []
            for c in range(sheet.ncols):
                ctype = sheet.cell_type(r, c)
                value = sheet.cell_value(r, c)
                if ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK, xlrd.XL_CELL_ERROR):
                    value = None
                elif ctype == xlrd.XL_CELL_DATE:
                    try:
                        value = xlrd.xldate_as_datetime(value, book.datemode)
                    except Exception:
                        pass
                row.append(value)
            rows.append(row)
        return rows

    if raw.startswith(b"PK"):                               # .xlsx
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
        finally:
            wb.close()

    if b"<table" in raw[:200000].lower():                   # HTML, сохранённый как .xls
        return _read_html(raw)

    raise ValueError("Не похоже на файл Excel (.xls / .xlsx): " + os.path.basename(path))


def find_columns(rows):
    """Ищет строку заголовков и номера нужных колонок."""
    for i, row in enumerate(rows[:60]):
        keys = [" ".join(str(v or "").replace("\xa0", " ").lower().split()) for v in row]
        if "номер пропуска" in keys and ("имя" in keys or "фио" in keys):
            col = {}
            for name, aliases in COLUMN_ALIASES.items():
                for alias in aliases:
                    if alias in keys:
                        col[name] = keys.index(alias)
                        break
            return i, col
    raise ValueError(
        "Не нашёл строку заголовков (ищу колонки «Имя» и «Номер пропуска»). "
        "Это точно выгрузка сотрудников из Sigur?")


def _cell(row, col, key):
    j = col.get(key)
    if j is None or j >= len(row):
        return ""
    return text(row[j])


# =====================================================================
#  Преобразование выгрузки
# =====================================================================

@dataclass
class Person:
    fio: str
    dept: str
    pos: str
    tab: str
    rtype: str


@dataclass
class Result:
    records: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    out_path: str = ""

    def summary(self):
        s = self.stats
        lines = [
            "Готово: строк для PERCo - %d (сотрудников - %d)." % (s["rows"], s["people"]),
            "Номеров пропусков пересчитано: %d; без пропуска: %d; не удалось разобрать: %d."
            % (s["cards_ok"], s["cards_empty"], s["cards_bad"]),
        ]
        if self.warnings:
            lines.append("Предупреждений: %d." % len(self.warnings))
        if self.out_path:
            lines.append("Файл: " + self.out_path)
        return "\n".join(lines)


def convert(rows, unlimited_until=UNLIMITED_UNTIL, upper=UPPERCASE_NAMES):
    """Строки выгрузки Sigur -> строки таблицы PERCo (18 колонок).

    Если у человека несколько пропусков, в выгрузке Sigur у второй и следующих
    строк имя/отдел/должность пустые - берём их от человека выше, и в PERCo
    получается по строке на каждый пропуск.
    """
    header_idx, col = find_columns(rows)
    res = Result()
    warn = res.warnings.append
    skipped_types = Counter()
    odd_modes = Counter()
    cur = None
    people = cards_ok = cards_empty = cards_bad = 0
    now_str = datetime.now().strftime("%Y-%m-%d 00:00:00")

    for idx in range(header_idx + 1, len(rows)):
        row = rows[idx]
        xl_row = idx + 1                                   # номер строки в Excel
        fio = " ".join(_cell(row, col, "fio").split())
        card_raw = _cell(row, col, "card").replace(" ", "")
        if not fio and not card_raw:
            continue

        if fio:
            cur = Person(fio, _cell(row, col, "dept"), _cell(row, col, "pos"),
                         _cell(row, col, "tab"), _cell(row, col, "type"))
            new_person = True
        else:
            if cur is None:
                warn("Строка %d: пропуск без владельца в начале файла - пропущен." % xl_row)
                continue
            new_person = False

        if ONLY_RECORD_TYPES and cur.rtype and cur.rtype.lower() not in ONLY_RECORD_TYPES:
            skipped_types[cur.rtype] += 1
            continue

        parts = cur.fio.split(" ")
        last, first, middle = parts[0], (parts[1] if len(parts) > 1 else ""), " ".join(parts[2:])
        if upper:
            last, first, middle = last.upper(), first.upper(), middle.upper()
        if new_person:
            people += 1
            if len(parts) < 2:
                warn("Строка %d: «%s» - в имени только одно слово (нет имени)." % (xl_row, cur.fio))
            if not cur.dept:
                warn("Строка %d: «%s» - не указан отдел (подразделение)." % (xl_row, cur.fio))

        # --- карта
        if not card_raw:
            perco_card = ""
            cards_empty += 1
        else:
            perco_card = sigur_to_perco_card(card_raw)
            if perco_card is None:
                warn("Строка %d: «%s» - не удалось разобрать номер пропуска «%s», карта оставлена пустой."
                     % (xl_row, cur.fio, card_raw))
                perco_card = ""
                cards_bad += 1
            else:
                cards_ok += 1

        # --- даты
        issued_raw = _cell(row, col, "issued")
        issued = parse_dt(issued_raw)
        if issued is not None:
            valid_from = issued.strftime(DT_FMT)
        elif issued_raw:
            valid_from = issued_raw
            warn("Строка %d: «%s» - непонятный формат времени выдачи «%s», оставлен как есть."
                 % (xl_row, cur.fio, issued_raw))
        else:
            valid_from = now_str
            warn("Строка %d: «%s» - нет времени выдачи, поставлена сегодняшняя дата." % (xl_row, cur.fio))
        hire_date = valid_from[:10]

        exp_raw = _cell(row, col, "expires")
        if not exp_raw or "не огранич" in exp_raw.lower():
            valid_until = unlimited_until
        else:
            exp = parse_dt(exp_raw)
            if exp is not None:
                valid_until = exp.strftime(DT_FMT)
            else:
                valid_until = exp_raw
                warn("Строка %d: «%s» - непонятный формат срока действия «%s», оставлен как есть."
                     % (xl_row, cur.fio, exp_raw))

        # --- режим пропуска
        mode = _cell(row, col, "mode")
        blocked = ""
        if "блок" in mode.lower():
            blocked = "Да"
        elif mode and mode.lower() != "по умолчанию":
            odd_modes[mode] += 1

        res.records.append([
            last, first, middle, blocked, cur.tab, hire_date, cur.dept, cur.pos,
            ACCESS_TEMPLATE, WORK_SCHEDULE, perco_card, "", valid_from, valid_until,
            "", "", "", 0,
        ])

    # --- сводные предупреждения
    for rtype, n in skipped_types.items():
        warn("Пропущено записей типа «%s»: %d (переносятся только: %s)."
             % (rtype, n, ", ".join(sorted(ONLY_RECORD_TYPES))))
    for mode, n in odd_modes.items():
        warn("Режим пропуска «%s» (%d шт.) в PERCo не переносится - пропуска будут обычными." % (mode, n))

    by_card = {}
    for rec in res.records:
        if rec[10]:
            by_card.setdefault(rec[10], []).append(rec)
    for card, recs in by_card.items():
        if len(recs) > 1:
            names = "; ".join("%s %s %s" % (r[0], r[1], r[2]) for r in recs)
            warn("Карта %s встречается %d раза (%s) - проверьте, не задвоена ли запись." % (card, len(recs), names))

    res.stats = {"rows": len(res.records), "people": people, "cards_ok": cards_ok,
                 "cards_empty": cards_empty, "cards_bad": cards_bad}
    return res


# =====================================================================
#  Запись файла для PERCo
# =====================================================================

def write_perco_table(records, path):
    """Только таблица: названия колонок в первой строке, данные со второй.

    Служебных строк отчёта сверху нет - импорт PERCo-Web их не принимает.
    XlsxWriter пишет файл так же, как сам Excel (sharedStrings, пустые ячейки
    не пишутся), текст - как текст, число - как число."""
    import xlsxwriter
    from xlsxwriter.exceptions import FileCreateError

    wb = xlsxwriter.Workbook(path, {"strings_to_numbers": False,
                                    "strings_to_formulas": False,
                                    "strings_to_urls": False})
    ws = wb.add_worksheet("Page 1")
    head = wb.add_format({"bold": True, "align": "center", "border": 1, "bg_color": "#BAD9FF"})

    for j, title in enumerate(PERCO_HEADERS):
        ws.write_string(0, j, title, head)
        ws.set_column(j, j, COLUMN_WIDTHS[j])

    for i, rec in enumerate(records, start=1):
        for j, value in enumerate(rec):
            if value is None or value == "":
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                ws.write_number(i, j, value)
            else:
                ws.write_string(i, j, str(value))

    try:
        wb.close()
    except FileCreateError as e:
        raise PermissionError(str(e)) from e


def default_output_path(src):
    folder = os.path.dirname(os.path.abspath(src))
    base = os.path.join(folder, "userPERCO_" + datetime.now().strftime("%Y-%m-%d_%H-%M"))
    path, n = base + ".xlsx", 2
    while os.path.exists(path):
        path = "%s_%d.xlsx" % (base, n)
        n += 1
    return path


def convert_file(src, dst=None, until=UNLIMITED_UNTIL, upper=UPPERCASE_NAMES):
    """Файл Sigur -> файл для импорта в PERCo. Возвращает Result."""
    until_dt = parse_dt(until)
    if until_dt is None:
        raise ValueError("Дата «Действует до» должна быть вида 2032-01-31 23:00:00, а не «%s»." % until)

    res = convert(read_table(src), until_dt.strftime(DT_FMT), upper)
    if not res.records:
        extra = ("\n" + "\n".join(res.warnings)) if res.warnings else ""
        raise ValueError("В файле не нашлось ни одного сотрудника для переноса." + extra)

    dst = dst or default_output_path(src)
    try:
        write_perco_table(res.records, dst)
    except PermissionError as e:
        raise PermissionError("Не удалось сохранить «%s». Если этот файл открыт в Excel - закройте его и повторите."
                              % dst) from e
    res.out_path = dst
    return res
