# FRONTEND-006: Страница избранного ⏳ 1 день

## Контекст
Проект Bina.ai: Telegram Mini App для аренды жилья в Грузии.
Фронтенд на **React + TypeScript + Vite** (`frontend/src/`). Структура из `docs/FRONTEND_BRIEF.md`
(`templates/*.html`, Alpine) устарела: страницы лежат в `src/pages/*.tsx`, компоненты в `src/components/`.

## Перед началом
Ветку создавать от **свежего `develop`**: в нём уже изменены `App.tsx` (basename роутера),
`vite.config.ts` и деплой (PR #18, #19). Иначе при мерже будет конфликт в `App.tsx`.
```bash
git checkout develop
git pull
git checkout -b feature/frontend-006-favorites
```

## Цель
Страница избранного со списком сохранённых квартир, удалением и счётчиком в шапке.
Пока данные хранятся в `localStorage`; позже переключим на готовый API `/api/favorites`
без переделки страницы.

## Требования

### 1. Хук `src/hooks/useFavorites.ts` (единственное место работы с хранилищем)
Сейчас `useFavorite()` хранит состояние только внутри кнопки: без ID квартиры и без сохранения.
Нужно заменить его общим хранилищем избранного:
- API хука: `ids: string[]`, `count`, `isFavorite(id)`, `add(id)`, `remove(id)`, `toggle(id)`.
- Хранение: `localStorage`, ключ `bina:favorites`, значение: JSON-массив **строк**.
- **ID квартир — строки (UUID)**, например `"3ba3a623-ed4c-4e61-966a-7bc071301186"`.
  Бэкенд (`GET /api/listings`) отдаёт UUID, а не числа. Не приводить к `number`, не проверять `/^\d+$/`.
  Числовые ID из `mock_data.json` сохранять как строки (`String(listing.id)`).
- Состояние общее для всех компонентов (Context-провайдер или `useSyncExternalStore`):
  изменение в карточке сразу видно в шапке и на странице избранного.
- Синхронизация между вкладками: событие `storage`.
- Повреждённое или пустое значение в `localStorage` не должно ломать приложение: считать пустым списком.
- Toast «Добавлено / Удалено» и haptic оставить как сейчас (перенести из `useFavorite`).

### 2. Кнопки «в избранное»
- `ListingCard.tsx` и `FavoriteButton.tsx` используют `useFavorites()` с ID своей квартиры:
  `toggle(listing.id)`, `isFavorite(listing.id)`.
- Старый `useFavorite.ts` удалить.

### 3. Страница `src/pages/FavoritesPage.tsx`
- Маршрут `/favorites` в `src/App.tsx` (ссылка в `Header.tsx` уже ведёт на него).
  Путь писать от корня (`/favorites`): префикс `/real-estate-rental` на GitHub Pages
  добавляет `basename` роутера.
- Данные квартир для списка: временно из `mock_data.json` / `/api/listings`, отфильтрованные по `ids`.
- Карточки: существующий `ListingCard`.
- Кнопка «Удалить из избранного» у каждой карточки (`remove(id)`); карточка исчезает сразу.
- **Empty state**, если избранное пустое: компонент `EmptyState` (иконка ♡, заголовок, текст)
  и кнопка «Найти квартиру», которая ведёт на `/`.
- Loading- и error-состояния, как на главной (`ListingSkeleton`, `ErrorState`).
- Заголовок страницы через `useDocumentTitle`, Telegram BackButton через `useTelegramBackButton`.

### 4. Счётчик в шапке
- В `Header.tsx` у ссылки ♡ показывать бейдж с `count`, если `count > 0`.
- `aria-label` вместе с числом, например «Избранное: 3».

### 5. Тексты (i18n)
Новые строки в `src/i18n/strings.ts` на 3 языках (ka, ru, en): заголовок страницы,
empty state, «Удалить из избранного», «Найти квартиру».

## Переход на API (следующая задача, не делать сейчас)
Бэкенд уже умеет хранить избранное на сервере (`docs/tasks/TASK-008-API.md`):
- `GET /api/favorites`: `{items, total, page, pages}`;
- `POST /api/favorites` с телом `{"listing_id": "<uuid>"}`;
- `DELETE /api/favorites/{listing_id}`.

Пользователь определяется по заголовку `X-Telegram-Init-Data`, `client.ts` его уже отправляет.
Когда будем переключаться, поменяется только `useFavorites.ts`.

## Definition of Done
1. Избранное сохраняется после перезагрузки страницы и видно во всех местах сразу
2. `/favorites` работает локально (`npm run dev`) и на GitHub Pages (`/real-estate-rental/favorites`)
3. Empty state при пустом списке, удаление работает
4. Счётчик в шапке обновляется без перезагрузки
5. ID хранятся строками, UUID с бэкенда поддерживаются
6. Тексты на 3 языках, адаптивно на 375 / 768 / 1024 px, нет горизонтального скролла
7. `npm run build` (с проверкой типов) проходит, Prettier без замечаний
8. Коммит: `feat(frontend): favorites page with localStorage`

## Запреты
- Работать с `localStorage` напрямую из компонентов (только через `useFavorites`)
- Хранить или сравнивать ID как числа
- Ставить `/real-estate-rental` в ссылках вручную (это делает `basename`)
