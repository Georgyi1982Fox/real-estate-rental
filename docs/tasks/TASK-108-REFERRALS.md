# TASK-108: Пригласи друга

## Правила
- У каждого своя ссылка: `https://t.me/<бот>?start=ref_<код>` (код из 8 символов).
- **Друг** получает скидку **20%** на первую покупку Premium: 250 ⭐ → 200 ⭐, 100 ⭐ → 80 ⭐.
- **Пригласивший** получает **7 дней Premium**, когда друг оплатит первый раз (если Premium уже
  есть — срок продлевается), и сообщение об этом.
- Защита от накрутки: не больше **10 наград в месяц**; приглашённым становится только новый
  пользователь (в боте — при первом `/start`, в Mini App — в первые сутки) и только один раз;
  себя пригласить нельзя; кто уже платил, скидку не получает.

## Бот
- `/invite` — ссылка, сколько приглашено и наград (команда добавлена в меню и /help).
- `/start ref_<код>` — новый пользователь запоминается как приглашённый, бот пишет о скидке.
- `/premium` — у приглашённого цены и кнопки со скидкой, счёт тоже со скидкой; при оплате
  принимается и полная цена, и цена со скидкой (если скидка положена).

## API (Mini App)
| Запрос | Что делает |
|---|---|
| `GET /api/referral` | `{"code", "link", "invited", "rewarded", "rewarded_this_month", "monthly_limit": 10, "reward_days": 7, "friend_discount_percent": 20}` |
| `POST /api/referral/apply` `{"code": "ref_xxxx"}` | Mini App открыли по ссылке `startapp=ref_<код>`: запомнить пригласившего. Ответ `{"applied": true, "discount_percent": 20}`; неверный код — 422 |
| `GET /api/subscription` | Новые поля: `discount_percent` и у каждого тарифа `price_stars_for_you` |
| `POST /api/subscription/invoice` | Счёт со скидкой, если она положена |

Имя бота для ссылки берётся из Telegram (`getMe`) один раз и запоминается.

## Заодно
- Счёт на оплату теперь и на грузинском (раньше для `ka` был английский).
- Исправлена ошибка схемы: у таблиц `bina_scrape_skips`, `bina_ai_usage`, `bina_complaints`
  не хватало колонок `created_at`/`updated_at` (миграция `timestamp_columns`); добавлен тест,
  что каждая модель читается из базы целиком.

Миграции `timestamp_columns` и `referrals` применяются сами при `update-bina.bat`.

## Код
`application/referrals.py`, `application/use_cases/referrals.py`,
`infrastructure/db/repositories/referrals.py`, `bot/handlers/invite.py`, `bot/handlers/start.py`,
`bot/handlers/payments.py`, `api/routes/referral.py`, `subscriptions.price_for`.

## Фронтенд
`FRONTEND-029-REFERRALS.md` (не выдана).
