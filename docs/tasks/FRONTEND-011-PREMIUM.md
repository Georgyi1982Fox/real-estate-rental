# FRONTEND-011: Premium-подписка в Mini App ⏳ 0,5–1 день

## Контекст
Проект Bina.ai: Telegram Mini App для аренды жилья в Грузии. Фронтенд на **React + TypeScript + Vite**
(`frontend/src/`). **Бэкенд готов** (`docs/tasks/TASK-016-SUBSCRIPTIONS.md`): оплата звёздами Telegram.

| | Бесплатно | Premium |
|---|---|---|
| Избранное | без ограничений | без ограничений |
| Сохранённые поиски | 1 | до 20 |
| Цена | — | 250 ⭐ за 30 дней |

## Перед началом
```bash
git checkout develop
git pull
git checkout -b feature/frontend-011-premium
```

## API
```
GET  /api/subscription           → Subscription
POST /api/subscription/invoice   тело { plan } → { url }
```
Нужен заголовок `X-Telegram-Init-Data` (клиент ставит его сам). Без него 401.

Типы в `src/api/types.ts`:
```ts
export interface Plan {
  id: string;          // "premium_month"
  tier: SubscriptionTier;
  days: number;
  price_stars: number;
}

export interface Subscription {
  tier: SubscriptionTier;          // "free" или "nomad" (= Premium)
  is_premium: boolean;
  expires_at: string | null;
  limits: { favorites: number | null; searches: number };  // null — без ограничения
  usage: { favorites: number; searches: number };
  plans: Plan[];
}
```
В `Me` добавилось поле `is_premium: boolean`. `subscription_tier` приходит уже с учётом срока
(истёкшая подписка — `free`), `subscription_expires_at` — только у действующей.

## Что сделать
1. **Хук `src/hooks/useSubscription.ts`**: `subscription`, `loading`, `error`, `reload()`, `buy(planId)`.
2. **Оплата `buy(planId)`**:
   ```ts
   const { url } = await apiPost('/api/subscription/invoice', { plan: planId });
   window.Telegram.WebApp.openInvoice(url, (status) => {
     // status: 'paid' | 'cancelled' | 'failed' | 'pending'
     if (status === 'paid') { haptic('success'); reload(); reloadMe(); }
   });
   ```
   Подписку включает бот после оплаты, это занимает 1–2 секунды: после `paid` перезапросить
   `/api/subscription` (при необходимости ещё раз через 2 секунды).
   Вне Telegram (`openInvoice` нет) кнопку не показывать, показать `OpenInTelegram`.
3. **Экран Premium** (`src/pages/PremiumPage.tsx`, маршрут `/premium`, внутри `Layout`):
   таблица «Бесплатно / Premium» (как выше, значения из `limits` и `plans`), цена в звёздах,
   кнопка **«Купить за 250 ⭐»** или, если Premium уже есть, «Premium до 28.10.2026» и «Продлить».
   Показать использование: «Поиски: 1 из 1». `limits.favorites` сейчас всегда `null` —
   избранное без ограничений, «из N» для него не показывать.
4. **Профиль**: бейдж тарифа («Бесплатный» / «Premium до …») и кнопка **«Улучшить»** → `/premium`.
5. **Ошибка 402** (`error.code === "payment_required"`) при сохранении поиска:
   не toast с ошибкой, а окно (`Modal`): «В бесплатном тарифе 1 сохранённый поиск»
   и кнопка «Подключить Premium» → `/premium`. Для избранного лимита больше нет, но
   обработчик 402 можно оставить общим.
   При откате оптимистичного ♥ (избранное) состояние сердечка вернуть назад.
6. **Тексты** на трёх языках (ka, ru, en) в `src/i18n/strings.ts`.

## Проверка
- `/premium` показывает цену и лимиты; «Купить» открывает окно оплаты Telegram.
- После оплаты профиль показывает «Premium до …» без перезапуска приложения.
- 2-й сохранённый поиск на бесплатном тарифе показывает окно «Подключить Premium»;
  избранное добавляется без ограничений.
- `npx tsc --noEmit` и `npm run build` без ошибок.

## Definition of Done
1. ⏳ Экран `/premium` с ценой, лимитами и оплатой через `openInvoice`
2. ⏳ Бейдж тарифа и кнопка «Улучшить» в профиле
3. ⏳ Обработка 402 с предложением Premium
4. ⏳ Тексты ka/ru/en
5. ⏳ Сборка и проверка типов проходят
