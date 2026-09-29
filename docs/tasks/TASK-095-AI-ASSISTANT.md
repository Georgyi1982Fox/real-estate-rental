# TASK-095: AI-помощник арендатора (Premium)

## Что умеет
| Запрос | Что делает | AI |
|---|---|---|
| `POST /api/listings/{id}/assistant` `{"action": "message_owner", "note": "…"}` | Вежливое первое сообщение хозяину **на грузинском** + перевод на язык пользователя | да |
| `POST /api/listings/{id}/assistant` `{"action": "viewing_questions", "note": "…"}` | 5-8 вопросов для просмотра именно этой квартиры (отопление зимой, коммунальные, депозит…) на языке пользователя | да |
| `GET /api/listings/{id}/cheaper` | До 5 похожих и дешевле: тот же район, те же комнаты (4+ вместе), площадь ±20%, сначала самые дешёвые | нет |

`note` (до 300 символов, необязательно) — о себе: «двое, с кошкой, с 1 ноября, на год».

Ответ помощника:
```json
{"action": "message_owner", "text_ka": "გამარჯობა! …", "translation": "Здравствуйте! …",
 "questions": [], "remaining_today": 29}
```

## Ограничения
- Только Premium, иначе **402** `payment_required`.
- Не больше `ASSISTANT_DAILY_LIMIT` (30) запросов к AI в день на пользователя, иначе **429**
  (`bina_ai_usage`, миграция `ai_usage`). «Похожие дешевле» в лимит не входят.
- AI не ответил — **502** «попробуйте ещё раз» (запрос засчитан). Нет `LLM_API_KEY` — **503**.

## Код
`application/ports/assistant.py`, `infrastructure/llm/assistant.py`,
`infrastructure/llm/prompts/assistant.py`, `infrastructure/api/routes/assistant.py`,
`ListingsRepository.cheaper_similar`, `repositories/users.py: take_ai_request`.

## Фронтенд
`FRONTEND-022-AI-ASSISTANT.md` (не выдана).
