# FRONTEND-050: Быстрый первый запуск — страницы грузятся по мере надобности

## Что сейчас
`npm run build` собирает весь сайт в один файл `index-*.js` — **937 КБ (258 КБ сжатый)**.
Все страницы импортируются в `App.tsx` сразу, поэтому при первом открытии Mini App
Telegram скачивает формы гостиниц, акты приёмки, кабинет агентства и т. д., хотя человек
открыл только поиск. Через туннель это заметно.

## Что сделать
1. Редкие страницы — отдельными частями (`React.lazy` + `Suspense` или `lazy` в
   `createBrowserRouter`):
   - формы: `HotelFormPage`, `ListingFormPage`, `AcceptancePage`;
   - личное: `MyDocumentsPage`, `MyHotelsPage`, `MyListingsPage`, `AgencyCabinetPage`,
     `ProfilePage`, `SavedSearchesPage`, `NotificationsPage`, `HistoryPage`, `InvitePage`;
   - остальное: `AgencyPage`, `ComparePage`, `PremiumPage`, `LegalPage`, `HelpPage`.

   Сразу (в основной части) остаются: `StartPage`, `HomePage`, `SearchPage`, `ListingPage`,
   `FavoritesPage`, `HotelsPage`, `HotelPage`, `MorePage`, `NotFoundPage`.
2. Пока часть грузится — лёгкая заглушка внутри `Layout` (шапка и нижняя панель на месте,
   без прыжков). Подойдут существующие `Skeleton` / `ListingSkeleton`.
3. После обновления сайта старые части удаляются. Если у человека открыта старая версия и
   часть не загрузилась (ошибка импорта) — один раз перезагрузить страницу
   (`window.location.reload()`, с отметкой в `sessionStorage`, чтобы не зациклиться).
4. Кнопка «Назад» Telegram, прокрутка и ссылки на страницы из бота (`?startapp=…`)
   работают как сейчас.

## Проверка
- `npm run build`: основной `index-*.js` не больше **~450 КБ** (≈130 КБ сжатый).
  Размеры до и после — в описании PR.
- Первый запуск `/rent` грузит не больше 3 JS-файлов; переход в «Мои объявления»
  догружает свою часть, и страница открывается.
- Открыть по очереди все страницы из «Ещё» — всё работает, ошибок в консоли нет.
- `npx tsc --noEmit` без ошибок.
