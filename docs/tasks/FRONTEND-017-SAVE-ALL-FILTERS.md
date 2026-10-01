# FRONTEND-017: «Сохранить поиск» — со всеми фильтрами

## Контекст
Бэкенд (TASK-086) теперь сохраняет в поиске все фильтры, а не только район, цену и комнаты.
Уведомления о новых квартирах приходят строго по ним.

## Перед началом
```bash
git checkout develop
git pull
git checkout -b feature/frontend-017-save-all-filters
```

**Уже сделано (FRONTEND-013, PR #94):** несколько районов (`districts`, `?district=a,b`),
`toSavedFilters()` и `filterEntries()` в `src/lib/searchFilters.ts` — расширять их, а не
писать заново.

## Что сделать
1. `SearchFilters` (`src/api/types.ts`) — добавить поля (имена как в `GET /api/listings`):
   `min_area`, `max_area`, `q`, `floor_min`, `floor_max`, `not_first_floor`,
   `not_last_floor`, `bedrooms`, `bathrooms`, `features: string[]`,
   `condition: string[]`, `owner_only`. Сервер в сохранённых поисках отдаёт ещё
   `city` (TASK-079) и `rent_period` (`monthly` / `daily`, TASK-092) — добавить их в тип
   и передавать как есть (выбор города и «посуточно» — отдельные задачи FRONTEND-030 и 032).
2. `SaveSearchButton` / `useSavedSearches.save()` → `POST /api/searches` с **текущими
   фильтрами целиком** (всё, что выбрано в панели фильтров и строке поиска).
3. `sameFilters()` / `FILTER_KEYS` / `filterEntries()` (`src/lib/searchFilters.ts`) —
   сравнивать и новые поля (`rent_period: 'monthly'` равен его отсутствию),
   иначе поиски с разными удобствами считаются одинаковыми. Заодно: API отдаёт незаданные
   поля как `null` (`"min_price": null`), а `entries()` отбрасывает только `undefined` и
   превращает `null` в строку `"null"` — поэтому сохранённый поиск без минимальной цены
   сейчас не совпадает с теми же фильтрами на странице. Пропускать и `null`, пустые списки,
   `false`.
4. Открытие сохранённого поиска (`SavedSearchesPage`) — применять все его фильтры к списку.
5. Карточка поиска (`SavedSearchCard`) — показывать выбранные дополнительные фильтры
   короткими чипами (этаж, удобства — названия из `src/i18n/features.ts`).

## Проверка
- Выбрать «не последний этаж» + «кондиционер» + «только собственник», сохранить поиск →
  `GET /api/searches` возвращает эти фильтры; при открытии поиска они снова выбраны.
- Два поиска, отличающиеся только удобствами, — разные.
- `npx tsc --noEmit` и `npm run build` без ошибок.
