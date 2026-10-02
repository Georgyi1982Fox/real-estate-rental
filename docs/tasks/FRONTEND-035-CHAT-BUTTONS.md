# FRONTEND-035: «Написать хозяину» и «Записаться на просмотр» на сайте

Вошла в FRONTEND-034 (раздел 5 «Кнопки на странице объявления хозяина»).

Бэкенд: у объявлений хозяев (`source=owner`) `source_url` и `POST /api/listings/{id}/contact`
ведут в бота — `https://t.me/<бот>?start=chat_<id>` (TASK-111), а не в личный Telegram
хозяина. Подробности — `docs/tasks/TASK-111-CHAT-VIEWINGS.md`.
