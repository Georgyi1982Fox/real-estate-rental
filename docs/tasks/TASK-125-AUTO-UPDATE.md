# TASK-125: Автообновление на компьютере владельца

## Зачем
После каждого мержа владелец сам запускал `update-bina.bat`. Облачная сессия Claude до его
компьютера не достаёт (Remote Control не отдаёт папку проекта облаку), поэтому обновляет сам
компьютер: раз в 10 минут проверяет GitHub и, если в `develop` есть новое, обновляется.

## Как устроено
- `auto-update-bina.ps1` — одна проверка:
  - Docker не запущен / ветка не `develop` / нет связи с GitHub — пропуск (запись в журнал);
  - `git fetch origin develop`; новых коммитов нет — «Обновлений нет»;
  - есть — `git pull --ff-only origin develop` и `docker compose up -d --build`
    (как `update-bina.bat`, 1–3 минуты сайт может не отвечать).
  - Журнал `auto-update.log` (в `.gitignore`), больше 1 МБ — в `auto-update.log.old`.
  - Файл в UTF-8 с BOM — иначе Windows PowerShell 5.1 читает русский текст как ANSI.
    PowerShell читает скрипт целиком до запуска, поэтому `git pull` может обновить и его самого.
- `auto-update-on.bat` — задание планировщика «Bina auto-update»: каждые 10 минут, пока
  владелец вошёл в Windows; `conhost.exe --headless` — без мелькающего окна. Сразу запускает
  первую проверку.
- `auto-update-off.bat` — удаляет задание; обновлять снова вручную (`update-bina.bat`).

## Владельцу (один раз)
1. `.\update-bina.bat` — скачать эти файлы.
2. `.\auto-update-on.bat` — включить.
3. Через минуту — `Get-Content auto-update.log -Tail 5`: строка «Обновлений нет» или «Готово».

Если журнал не появился — `conhost --headless` не поддерживается этой Windows: тогда задание
пересоздать без него (`powershell.exe -WindowStyle Hidden -File …`).

## Дальше
Окна туннелей (`start-bina.bat`) автообновление не трогает. После переезда на сервер
(TASK-088) — обновление на сервере по мержу (GitHub Actions), это задание не нужно.
