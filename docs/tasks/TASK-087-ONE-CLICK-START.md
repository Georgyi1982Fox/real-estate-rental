# TASK-087: Запуск одним кликом (Windows)

Три файла в корне проекта, запускаются двойным кликом в Проводнике:

| Файл | Что делает |
|---|---|
| `start-bina.bat` | Запускает Docker Desktop (если выключен) и ждёт его; `docker compose up -d`; открывает окно туннеля (`cloudflared tunnel run realtybot-dev`) и окно сайта (`npm run dev -- --host 127.0.0.1`) |
| `update-bina.bat` | `git checkout develop` + `git pull`, `docker compose up -d --build`, `npm install` для сайта |
| `stop-bina.bat` | `docker compose stop` (данные базы сохраняются) |

После перезагрузки компьютера — только `start-bina.bat`. После сообщения «смержил» —
`update-bina.bat`, затем закрыть окно сайта и снова `start-bina.bat`.

Окна «Bina - tunnel» и «Bina - site» закрывать нельзя, пока приложение нужно.
Файлы в CRLF (`.gitattributes`: `*.bat text eol=crlf`), тексты в UTF-8 (`chcp 65001`).
