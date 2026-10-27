# TASK-087: Запуск одним кликом (Windows)

Три файла в корне проекта, запускаются двойным кликом в Проводнике:

| Файл | Что делает |
|---|---|
| `start-bina.bat` | Запускает Docker Desktop (если выключен) и ждёт его; `docker compose up -d` (вместе с сайтом Mini App — сервис `web`, TASK-123); открывает окно туннеля (`cloudflared tunnel run realtybot-dev`). Окна сайта (`npm run dev`) больше нет |
| `update-bina.bat` | `git checkout develop` + `git pull`, закрывает старое окно сайта, `docker compose up -d --build` (сайт пересобирается там же) |
| `stop-bina.bat` | `docker compose stop` (данные базы сохраняются) |
| `backup-now.bat` | Копия базы сейчас (TASK-044) |
| `restore-bina.bat` | Восстановить базу из копии (TASK-045) |

После перезагрузки компьютера — только `start-bina.bat`. После сообщения «смержил» —
`update-bina.bat` — и всё (сайт обновляется вместе с остальным, TASK-123).

Окно «Bina - tunnel» закрывать нельзя, пока приложение нужно (окна «Bina - site» больше нет).
Файлы в CRLF (`.gitattributes`: `*.bat text eol=crlf`), тексты в UTF-8 (`chcp 65001`).
