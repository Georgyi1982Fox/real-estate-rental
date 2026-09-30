# FRONTEND-029: «Пригласи друга»

## Контекст (бэкенд TASK-108)
`GET /api/referral`, `POST /api/referral/apply`, в `GET /api/subscription` — `discount_percent`
и `plans[].price_stars_for_you`. Подробности — `docs/tasks/TASK-108-REFERRALS.md`.

## Что сделать
1. **При запуске Mini App**: если `Telegram.WebApp.initDataUnsafe.start_param` начинается
   с `ref_`, один раз вызвать `POST /api/referral/apply {"code": start_param}`. Если
   `discount_percent > 0` — показать плашку «🎁 Вам скидка 20% на первый Premium».
2. **Экран Premium**: показывать `price_stars_for_you`; если она меньше `price_stars` —
   старую цену зачеркнуть. Плашка про скидку, если `discount_percent > 0`.
3. **Профиль → «Пригласить друга»**: условия (друг −20%, вам +7 дней Premium, до 10 в месяц),
   кнопка «Поделиться» — `Telegram.WebApp.openTelegramLink("https://t.me/share/url?url=" +
   encodeURIComponent(link))`, кнопка «Скопировать ссылку», счётчики «Приглашено / Наград».
4. Все тексты ka / ru / en.

## Проверка
- Открыть Mini App по ссылке друга новым аккаунтом → плашка о скидке, цены −20%.
- `npx tsc --noEmit` и `npm run build` без ошибок.
