# TASK-016: Подписка Premium за звёзды Telegram

> В `BACKEND_ROADMAP.md` это **TASK-026 «Подписки»** и **TASK-027 «Telegram Stars»**.

## Тарифы
| | Бесплатно | Premium |
|---|---|---|
| Избранное | без ограничений | без ограничений |
| Сохранённые поиски (с уведомлениями) | 1 | до 20 |
| Цена | — | 250 ⭐ за 30 дней |

Цена и срок настраиваются в `.env`: `PREMIUM_PRICE_STARS`, `PREMIUM_DAYS`. В базе тариф Premium
хранится как `nomad` (`bina_users.subscription_tier`).

- Истёкшая подписка автоматически считается бесплатной (API и бот смотрят на `subscription_expires_at`).
- Повторная оплата продлевает подписку **от даты окончания**, если она ещё действует.
- Если лимит уже превышен (например, было 3 поиска до введения лимитов), существующее не удаляется:
  нельзя только добавить новое. Убрать из избранного можно всегда.

## Оплата
Звёзды Telegram (валюта `XTR`), `provider_token` не нужен, настраивать в BotFather ничего не надо.

1. Счёт: в боте `/premium` → «Купить за 250 ⭐»; в Mini App `POST /api/subscription/invoice` →
   `Telegram.WebApp.openInvoice(url)`. Payload счёта: `sub:premium_month`.
2. `pre_checkout_query`: бот проверяет тариф, валюту и сумму и отвечает за ≤ 10 секунд.
3. `successful_payment`: платёж пишется в `bina_payments` (`provider=telegram_stars`,
   `provider_payment_id` = `telegram_payment_charge_id`, `plan`), подписка продлевается.
   Повторная доставка того же платежа ничего не меняет (уникальный `provider_payment_id`).
4. `/paysupport` — обязательная для Stars команда поддержки. Возврат звёзд делается вручную
   (`refundStarPayment` с `telegram_payment_charge_id` из `bina_payments`).

**Важно:** оплату принимает **бот** (`docker compose` сервис `bot`). Если бот не запущен, Telegram
не сможет провести платёж (не получит ответ на `pre_checkout_query`) — деньги не спишутся.

## API
```
GET  /api/subscription           → { tier, is_premium, expires_at, limits, usage, plans }
POST /api/subscription/invoice   тело { plan: "premium_month" } → { url }
                                  404 — нет тарифа; 503 — не задан BOT_TOKEN
```
```json
{
  "tier": "free", "is_premium": false, "expires_at": null,
  "limits": { "favorites": null, "searches": 1 },
  "usage": { "favorites": 3, "searches": 1 },
  "plans": [{ "id": "premium_month", "tier": "nomad", "days": 30, "price_stars": 250 }]
}
```
`limits.favorites: null` — без ограничения.

Изменения в существующих эндпоинтах:
- `POST /api/favorites`, `POST /api/searches`: **402** `payment_required`, если лимит тарифа исчерпан
  (раньше для поисков было 409 после 20).
- `GET /api/me`: `subscription_tier` с учётом срока (истёкшая — `free`), новое поле `is_premium`,
  `subscription_expires_at` только у действующей подписки.

## Что сделано
| Слой | Файлы |
|---|---|
| Политика | `application/subscriptions.py`: тарифы, лимиты, `is_premium`, проверка счёта, продление |
| Use case | `application/use_cases/subscriptions.py`: `ActivateSubscriptionUseCase` (идемпотентный) |
| БД | модель `Payment` (исправлены `gen_random_uuid()` и enum-ы), поле `plan` (миграция `payments_plan`), `PaymentsRepository`, `UsersRepository.set_subscription`; `subscription_expires_at` с часовым поясом, как в миграции |
| API | `routes/subscription.py`, лимиты в `favorites.py` и `searches.py`, код ошибки 402 |
| Бот | `handlers/payments.py`: `/premium`, счёт, `pre_checkout_query`, `successful_payment`, `/paysupport`; лимит в ☆ избранного; тариф в профиле |
| Тесты | политика, use case, API (402, счёт), бот (оплата, повтор, продление, неверный счёт), PostgreSQL |

## Проверка вручную
1. `docker compose up -d --build`.
2. В боте `/premium` → «Купить за 250 ⭐» → оплатить (нужны звёзды на аккаунте; для проверки можно
   временно поставить `PREMIUM_PRICE_STARS=1` в `.env` и снова `docker compose up -d --build`).
3. Бот отвечает «Premium действует до …», в `/profile` — «Подписка: Premium (до …)».

## Definition of Done
1. ✅ Лимиты бесплатного тарифа в API и боте
2. ✅ Оплата звёздами в боте, счёт для Mini App
3. ✅ Платежи в БД, идемпотентность, продление
4. ✅ Тесты, в том числе на PostgreSQL
5. ⏳ Кнопка «Улучшить» и экран Premium в Mini App — FRONTEND-011
