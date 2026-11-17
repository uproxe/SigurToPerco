## Какой файл скачать

| Система | Файл | Как запустить |
|---|---|---|
| Windows 10/11 | `SigurPerco-…-windows-x64.exe` | просто запустить, установка не нужна |
| Windows 7 | `SigurPerco-…-windows-x64-win7.exe` | то же, для старых компьютеров |
| Ubuntu / Debian / Astra и др. | `sigur-perco_…_amd64.deb` | `sudo apt install ./sigur-perco_…_amd64.deb`, затем «Sigur → PERCo» в меню |
| Linux без установки | `SigurPerco-…-linux-x64.tar.gz` | распаковать и запустить `SigurPerco/SigurPerco` |
| macOS (M1/M2/M3/M4) | `SigurPerco-…-macos-arm64.dmg` | перетащить в «Программы»; первый запуск — см. ниже |
| macOS (Intel) | `SigurPerco-…-macos-intel.dmg` | то же |

**macOS, первый запуск.** Программа не подписана сертификатом Apple, поэтому система
её сначала не пустит. Откройте «Системные настройки → Конфиденциальность и безопасность»
и нажмите «Всё равно открыть». Или один раз выполните в Терминале:
`xattr -dr com.apple.quarantine /Applications/SigurPerco.app`

**Windows.** SmartScreen может предупредить о неизвестном издателе: «Подробнее → Выполнить в любом случае».
