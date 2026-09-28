# FRONTEND-010: Страница уведомлений ⏳ 1 день

## Контекст
Проект Bina.ai: Telegram Mini App для аренды жилья в Грузии.
Фронтенд на **React + TypeScript + Vite** (`frontend/src/`): страницы в `src/pages/*.tsx`,
компоненты в `src/components/`. Шаблоны `templates/pages/*.html` из исходного плана устарели.

Уведомления приходят по **сохранённым поискам** (FRONTEND-009) и по **избранному**.
Те же уведомления бэкенд отправляет в Telegram через бота.

## Перед началом
Делать **после FRONTEND-009** (ссылки ведут на `/searches`). Ветку создавать от свежего `develop`:
```bash
git checkout develop
git pull
git checkout -b feature/frontend-010-notifications
```

**Бэкенд `/api/notifications` готов** (TASK-028, `docs/tasks/TASK-012-NOTIFICATIONS.md`). Хук всё
равно пишется с запасом: при ошибке сети — mock-данные.

## Типы уведомлений
Уведомлений «новое сообщение» не будет: чата нет.

| `type` | Когда | Иконка | Текст (собирается на фронтенде из `strings.ts`) |
|---|---|---|---|
| `new_listing` | новая квартира по сохранённому поиску | 🏠 | «Новая квартира: {title} — {price}», ниже «по поиску «{search_name}»» |
| `price_drop` | снизилась цена квартиры из избранного | 📉 | «Цена снижена: {old_price} → {price}» |
| `system` | служебное (подписка и т. п.) | ℹ️ | `text` с сервера |

## API (бэкенд TASK-028, готов)
```
GET  /api/notifications?filter=all|unread&page=1&per_page=20
     → { items: AppNotification[], total, page, pages, unread_count }
GET  /api/notifications/unread-count     → { count }
POST /api/notifications/{id}/read        → 204
POST /api/notifications/read-all         → 204
```
Нужен заголовок `X-Telegram-Init-Data` (клиент ставит его сам). Без него ответ 401.

Типы в `src/api/types.ts`:
```ts
export type NotificationType = 'new_listing' | 'price_drop' | 'system';

export interface NotificationListing {
  id: string;
  title: Localized;
  price: number;
  currency: string;
  image?: string | null;
}

export interface AppNotification {
  id: string;
  type: NotificationType;
  created_at: string;
  is_read: boolean;
  listing?: NotificationListing | null;  // для new_listing и price_drop
  old_price?: number | null;             // для price_drop
  search_id?: string | null;             // для new_listing
  search_name?: string | null;
  text?: Localized | null;               // для system
}

export interface NotificationsPage {
  items: AppNotification[];
  total: number;
  page: number;
  pages: number;
  unread_count: number;
}
```

## Что сделать
1. **Хук `src/hooks/useNotificationFeed.ts`** (имя `useNotifications.ts` уже занято настройкой
   «Уведомления» в профиле): список, `unreadCount`, `markRead(id)`, `markAllRead()`,
   фильтр `all`/`unread`, пагинация. Сначала API; при 404 или ошибке сети — mock из
   **4–5 уведомлений** разных типов, прочитанность хранить в `localStorage` (`bina:notifications_read`).
2. **Страница `src/pages/NotificationsPage.tsx`, маршрут `/notifications`** (в `App.tsx`, внутри `Layout`):
   - **табы «Все» / «Непрочитанные»**, у второго число непрочитанных;
   - **карточка уведомления:** иконка типа, текст, фото квартиры (если есть), время
     («5 мин назад», «вчера»; функцию добавить в `src/lib/format.ts`, на трёх языках);
     непрочитанные выделены точкой или фоном;
   - нажатие **помечает прочитанным** и для `new_listing` и `price_drop` открывает `/listing/{id}`;
   - кнопка **«Прочитать все»** (видна, если есть непрочитанные);
   - **empty state** для обоих табов: «Уведомлений пока нет. Сохраните поиск — пришлём новые квартиры»,
     кнопка на `/searches`;
   - скелетоны при загрузке, `ErrorState` при ошибке, 401 или вне Telegram — `OpenInTelegram`;
   - пагинация (компонент `Pagination` уже есть) или «Показать ещё».
3. **Колокольчик с бейджем** в `src/components/Header.tsx`: число непрочитанных
   (`9+`, если больше 9), ведёт на `/notifications`. Число обновлять раз в минуту и при
   возврате на вкладку (`visibilitychange`). Гостю колокольчик не показывать.
4. **Настройка «Уведомления» в профиле** (сейчас в `localStorage`) пока остаётся как есть,
   к серверу её подключим отдельно.
5. **Тексты** на трёх языках (ka, ru, en) в `src/i18n/strings.ts`.

## Проверка
- Колокольчик показывает число непрочитанных; после «Прочитать все» оно пропадает.
- Таб «Непрочитанные» показывает только непрочитанные; прочитанная карточка из него исчезает.
- Нажатие на уведомление открывает квартиру.
- Empty state виден, если уведомлений нет.
- Без бэкенда всё работает на mock-данных.
- `npx tsc --noEmit` и `npm run build` без ошибок.

## Definition of Done
1. ⏳ Страница `/notifications`: табы, карточки, отметка прочитанного, «Прочитать все», empty state
2. ⏳ Колокольчик с бейджем в шапке
3. ⏳ Хук с API и mock-запасом
4. ⏳ Относительное время на трёх языках
5. ⏳ Тексты ka/ru/en
6. ⏳ Сборка и проверка типов проходят
