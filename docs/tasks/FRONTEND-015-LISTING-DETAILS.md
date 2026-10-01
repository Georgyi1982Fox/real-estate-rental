# FRONTEND-015: Все характеристики на странице объявления ⏳ 0,5–1 день

## Контекст
Проект Bina.ai: Telegram Mini App для аренды жилья в Грузии. Фронтенд на **React + TypeScript + Vite**
(`frontend/src/`). Бэкенд теперь берёт со страницы объявления на сайте всё
(`docs/tasks/TASK-018-LISTING-DETAILS.md`): этажи, спальни, санузлы, состояние, удобства, адрес,
координаты, собственник или агентство, даты. Их нужно показать на странице объявления.

## Перед началом
```bash
git checkout develop
git pull
git checkout -b feature/frontend-015-listing-details
```

## API (готов)
`GET /api/listings/{id}` (и списки) — новые поля в `Listing` (`src/api/types.ts`):
```ts
export type FeatureCode =
  | 'furniture' | 'kitchen_appliances' | 'air_conditioning' | 'heating' | 'hot_water'
  | 'washing_machine' | 'dishwasher' | 'fridge' | 'tv' | 'internet' | 'gas' | 'elevator'
  | 'parking' | 'balcony' | 'storage' | 'pool' | 'pets_allowed' | 'security';

export type ConditionCode =
  | 'newly_renovated' | 'renovated' | 'needs_renovation' | 'under_renovation'
  | 'white_frame' | 'black_frame' | 'green_frame';

export interface Listing {
  // ...
  floor: number | null;
  total_floors: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  condition: ConditionCode | null;
  features: FeatureCode[];
  owner_type: 'owner' | 'agent' | null;
  address: Localized;           // {ka, ru, en}: улица на всех языках (TASK-019), {} — сайт не указал
  owner?: { name: Localized };   // имя владельца на ka/ru/en (транслитерация)
  latitude: number | null;
  longitude: number | null;
  published_at: string | null;  // опубликовано на сайте
  updated_at: string | null;    // обновлено на сайте
}
```
`null` — сайт не указал: такую строку не показывать. Неизвестный код — не показывать.

**Уже сделано (TASK-019):** `src/i18n/features.ts` — названия всех 18 кодов удобств на трёх
языках, `ListingSpecs` берёт их оттуда (неизвестный код не показывается). Адрес и имя владельца
приложение уже показывает через `tr(...)` на языке интерфейса.

## Что сделать
1. **Блок «Характеристики»** (`ListingSpecs`, уже есть — расширить): таблица «название — значение»:
   комнаты, спальни, санузлы, площадь, этаж «4 из 9», состояние, «Собственник» / «Агентство».
2. **Блок «Удобства»**: сетка иконок с подписями для каждого кода из `features`
   (мебель 🛋, кондиционер ❄️, стиральная машина, лифт, парковка, балкон, животные 🐾 и т. д.).
3. **Адрес** под заголовком: 📍 «ул. Мачабели 6, Сололаки». При наличии координат — ссылка
   «На карте» → `https://www.google.com/maps?q={latitude},{longitude}` (открыть через
   `Telegram.WebApp.openLink`).
4. **Даты** внизу: «Опубликовано 31 августа · обновлено вчера» (относительное время —
   функция из FRONTEND-010 в `src/lib/format.ts`).
5. **Карточка в списке** (`ListingCard`): к «2 комн. · 68 м²» добавить «4/9 эт.» и значок
   «Собственник», если `owner_type === 'owner'` (так помечены и объявления, которые
   собственники разместили сами через бота, TASK-096). Значок ⚠️ мошенничества (FRONTEND-012)
   не трогать — он остаётся в углу фото.
6. **Описание**: сохранять переносы строк (`white-space: pre-line`), длинное — «Показать полностью».
7. **Тексты** на трёх языках (ka, ru, en): названия состояний (по образцу `src/i18n/features.ts`)
   и подписи характеристик; ключ `listing.features` в `strings.ts` больше не нужен — можно удалить.

## Проверка
- Объявление с SS.ge: видны этаж, санузлы, состояние, удобства иконками, адрес, «На карте».
- Переключение языка меняет подписи удобств и состояния.
- Объявление без подробностей (ещё не дозагружено) выглядит как раньше, без пустых строк.
- `npx tsc --noEmit` и `npm run build` без ошибок.

## Definition of Done
1. ⏳ Характеристики и удобства на странице объявления
2. ⏳ Адрес и ссылка на карту
3. ⏳ Даты публикации/обновления
4. ⏳ Этажность и «Собственник» в карточке списка
5. ⏳ Тексты ka/ru/en
6. ⏳ Сборка и проверка типов проходят
