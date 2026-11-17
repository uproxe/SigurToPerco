import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from sigur_perco import core  # noqa: E402
from sample_export import write_sample_html_xls, write_sample_xlsx  # noqa: E402


# ---------------------------------------------------------------- номера

@pytest.mark.parametrize("sigur, perco", [
    ("000000AB12CD34", "18/52532"),
    ("12CD34", "18/52532"),
    ("w58: 0000 00ab 12cd 34", "18/52532"),
    ("000000ABFF0001", "255/1"),
    ("000000AB000000", "0/0"),
])
def test_sigur_to_perco(sigur, perco):
    assert core.sigur_card(sigur).perco == perco


def test_card_parts():
    r = core.sigur_card("000000AB12CD34")
    assert (r.hex6, r.series, r.number) == ("12CD34", 18, 52532)


@pytest.mark.parametrize("bad", ["", None, "12345", "ZZZZ"])
def test_sigur_bad(bad):
    with pytest.raises(ValueError):
        core.sigur_card(bad)


@pytest.mark.parametrize("perco, hex6", [("18/52532", "12CD34"), (" 255 / 1 ", "FF0001"), ("0\\0", "000000")])
def test_perco_to_sigur(perco, hex6):
    assert core.perco_to_sigur(perco) == hex6


@pytest.mark.parametrize("bad", ["256/1", "1/65536", "abc", "18-52532", ""])
def test_perco_bad(bad):
    with pytest.raises(ValueError):
        core.perco_to_sigur(bad)


def test_round_trip():
    for series, number in [(0, 0), (18, 52532), (255, 65535), (127, 1)]:
        h = core.perco_to_sigur("%d/%d" % (series, number))
        assert core.sigur_card(h).perco == "%d/%d" % (series, number)


def test_convert_any():
    assert core.convert_any("000000AB12CD34") == "18/52532"
    assert core.convert_any("18/52532") == "12CD34"


# ---------------------------------------------------------------- выгрузка

@pytest.fixture
def sample_xlsx(tmp_path):
    return write_sample_xlsx(str(tmp_path / "export.xlsx"))


def test_convert_file(sample_xlsx, tmp_path):
    out = str(tmp_path / "out.xlsx")
    res = core.convert_file(sample_xlsx, out)
    assert res.out_path == out

    recs = {(r[0], r[10]): r for r in res.records}
    assert len(res.records) == 7                       # гость пропущен, у Петровой 2 строки
    assert res.stats["people"] == 6

    ivanov = recs[("Иванов", "18/52532")]
    assert ivanov[:3] == ["Иванов", "Иван", "Иванович"]
    assert ivanov[4] == "1001"                         # табельный - текстом, без .0
    assert ivanov[5] == "2024-03-11"
    assert ivanov[12] == "2024-03-11 09:15:00"
    assert ivanov[13] == core.UNLIMITED_UNTIL
    assert ivanov[17] == 0

    second = recs[("Петрова", "10/6957")]              # 0A1B2D - второй пропуск
    assert second[3] == "Да"                           # блокировка
    assert second[6] == "Цех №1"                       # отдел взят от строки выше
    assert second[13] == "2026-12-31 23:59:59"

    assert recs[("Сидоров", "255/1")][12] == "2024-04-12 08:00:00"   # формат дд.мм.гггг
    assert recs[("Кузнецова", "")][10] == ""                        # без пропуска
    assert recs[("Волков", "127/255")][10] == "127/255"              # «W58: …» с пробелами

    w = "\n".join(res.warnings)
    assert "Посетитель" in w
    assert recs[("Сидоров", "255/1")][1:3] == ["Пётр", ""]           # без отчества - не ошибка
    assert "не указан отдел" in w
    assert "НЕТ-НОМЕРА" in w
    assert "Особый" in w
    assert "нет времени выдачи" in w


def test_output_file_layout(sample_xlsx, tmp_path):
    from openpyxl import load_workbook
    out = str(tmp_path / "out.xlsx")
    core.convert_file(sample_xlsx, out)
    ws = load_workbook(out).active
    rows = list(ws.iter_rows(values_only=True))
    assert list(rows[0]) == core.PERCO_HEADERS          # шапка - в первой строке
    assert rows[1][0] == "Иванов"                       # данные - сразу со второй
    assert isinstance(rows[1][4], str)                  # табельный - текст
    assert rows[1][17] == 0 and isinstance(rows[1][17], int)
    head = ws["A1"]
    assert head.font.b and head.fill.fgColor.rgb.endswith("BAD9FF")


def test_options(sample_xlsx, tmp_path):
    res = core.convert_file(sample_xlsx, str(tmp_path / "o.xlsx"), until="2030-01-01", upper=True)
    ivanov = res.records[0]
    assert ivanov[0] == "ИВАНОВ"
    assert ivanov[13] == "2030-01-01 00:00:00"


def test_bad_until(sample_xlsx, tmp_path):
    with pytest.raises(ValueError):
        core.convert_file(sample_xlsx, str(tmp_path / "o.xlsx"), until="когда-нибудь")


def test_html_xls(tmp_path):
    src = write_sample_html_xls(str(tmp_path / "export.xls"))
    res = core.convert_file(src, str(tmp_path / "out.xlsx"))
    assert len(res.records) == 7
    assert res.records[0][10] == "18/52532"


def test_not_excel(tmp_path):
    p = tmp_path / "x.xls"
    p.write_bytes(b"hello")
    with pytest.raises(ValueError):
        core.read_table(str(p))


def test_no_header():
    with pytest.raises(ValueError):
        core.convert([["что-то"], ["ещё"]])


def test_default_output_path_unique(tmp_path):
    src = str(tmp_path / "export.xlsx")
    first = core.default_output_path(src)
    open(first, "w").close()
    assert core.default_output_path(src) != first


# ---------------------------------------------------------------- консоль

def test_cli_card(capsys):
    from sigur_perco.__main__ import main
    assert main(["--card", "000000AB12CD34"]) == 0
    assert capsys.readouterr().out.strip() == "18/52532"


def test_cli_convert(sample_xlsx, tmp_path, capsys):
    from sigur_perco.__main__ import main
    out = str(tmp_path / "cli.xlsx")
    assert main(["--cli", sample_xlsx, "-o", out]) == 0
    assert os.path.exists(out)
    assert "строк для PERCo - 7" in capsys.readouterr().out
