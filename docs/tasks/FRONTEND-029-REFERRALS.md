# FRONTEND-029: «Пригласи друга»

**Бэкенд готов** (TASK-108, подробности — `TASK-108-REFERRALS.md`). Друг по ссылке
получает скидку на первый Premium, пригласивший — дни Premium, когда друг оплатит.

## Контекст (бэкенд)
- `GET /api/referral` → `{code, link, invited, rewarded, rewarded_this_month,
  monthly_limit, reward_days, friend_discount_percent}`. 503 — бот не настроен (блок скрыть).
- `POST /api/referral/apply` `{code}` → `{applied, discount_percent}`.
- `GET /api/subscription` → `discount_percent` и в `plans[]` — `price_stars_for_you`
  (цена со скидкой для этого человека).

**Цифры условий не писать в текстах вручную** — брать из ответа:
`friend_discount_percent` (сейчас 20), `reward_days` (7), `monthly_limit` (10).

## Что сделать
1. **Запуск Mini App по ссылке друга.** Если `Telegram.WebApp.initDataUnsafe.start_param`
   начинается с `ref_` — один раз (запомнить в `localStorage`) вызвать
   `POST /api/referral/apply {"code": start_param}`. Если `discount_percent > 0` — плашка
   «🎁 Вам скидка {discount_percent}% на первый Premium».
2. **Экран Premium.** Показывать `price_stars_for_you`; если меньше `price_stars` — старую
   цену зачеркнуть и рядом «−{discount_percent}%».
3. **Профиль → «🎁 Пригласить друга»** (пункт в меню профиля и плитка на главной-хабе):
   - условия: «Другу — скидка {friend_discount_percent}% на первый Premium, вам —
     +{reward_days} дней Premium за каждого, кто оплатит (до {monthly_limit} в месяц)»;
   - кнопка «Поделиться» → `Telegram.WebApp.openTelegramLink("https://t.me/share/url?url=" +
     encodeURIComponent(link))`; в браузере — скопировать ссылку и тост «Ссылка скопирована»;
   - счётчики «Приглашено: {invited}» и «Награды: {rewarded}».
4. Тексты на трёх языках (ka / ru / en).

## Проверка
- Открыть Mini App по ссылке друга новым аккаунтом → плашка о скидке, цены в Premium
  со скидкой.
- В профиле пригласившего счётчик «Приглашено» вырос.
- `npx tsc --noEmit` и `npm run build` без ошибок.
