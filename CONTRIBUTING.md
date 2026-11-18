# Как вносить изменения

## Подготовка

```bash
git clone https://github.com/uproxe/SigurToPerco.git
cd SigurToPerco
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python run.py
```

На Linux для окна нужен tkinter: `sudo apt install python3-tk`.

## Перед коммитом

```bash
python -m ruff check .              # стиль и типичные ошибки
python -m pytest                    # тесты логики
python scripts/screenshots.py       # окно «вживую», снимки в screenshots/
```

Код должен оставаться совместимым с **Python 3.8** — на нём собирается версия для Windows 7
(линтер настроен на эту версию и подскажет, если что-то не подходит).

## Где что лежит

- логика пересчёта и файлов — `sigur_perco/core.py` (без интерфейса, покрыта тестами);
- окно — `sigur_perco/gui.py`, элементы интерфейса — `sigur_perco/widgets.py`;
- сборка — `scripts/build.py`, GitHub Actions — `.github/workflows/build.yml`.

## Сообщения коммитов

По [Conventional Commits](https://www.conventionalcommits.org/ru/v1.0.0/):
`feat: …` — новое, `fix: …` — исправление, `docs: …`, `ci: …`, `refactor: …`, `test: …`, `chore: …`.

## Выпуск версии

Версии — по [SemVer](https://semver.org/lang/ru/): `MAJOR.MINOR.PATCH`.

1. Поменять `__version__` в `sigur_perco/__init__.py`.
2. В `CHANGELOG.md` перенести пункты из «Не выпущено» в новый раздел `## [X.Y.Z] - ГГГГ-ММ-ДД`
   и добавить ссылку на версию внизу файла.
3. Закоммитить и поставить тег:

   ```bash
   git tag -a vX.Y.Z -m "Sigur → PERCo X.Y.Z"
   git push origin main vX.Y.Z
   ```

GitHub Actions проверит, что тег совпадает с версией в коде и что в CHANGELOG есть раздел,
соберёт программу под все системы и опубликует Release с описанием из CHANGELOG.

## Важно: персональные данные

Настоящие выгрузки из Sigur и файлы для PERCo содержат персональные данные сотрудников.
**Не добавляйте их в репозиторий и не прикладывайте к issue.** Для примеров есть
`examples/sigur_export_sample.xlsx` с вымышленными людьми (пересоздаётся `scripts/make_sample.py`).
