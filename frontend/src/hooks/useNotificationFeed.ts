import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';
import { ApiError, apiGet, apiPost } from '../api/client';
import type { AppNotification, NotificationsPage, UnreadCountResponse } from '../api/types';
import { APP_BASE } from '../lib/config';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

// Лента уведомлений (новые квартиры по сохранённым поискам, снижение цены в избранном).
// Сначала — бэкенд /api/notifications. Пока его нет (404) или нет сети, работаем
// с mock-данными, а прочитанность храним в localStorage. Когда бэкенд появится,
// хук перейдёт на него без переделок.
//
// Имя useNotifications.ts занято настройкой «Уведомления» в профиле.
const API_PATH = '/api/notifications';
const READ_KEY = 'bina:notifications_read';
const PER_PAGE = 20;
const POLL_INTERVAL = 60_000;

export type NotificationFilter = 'all' | 'unread';

const MINUTE = 60_000;
const ago = (minutes: number) => new Date(Date.now() - minutes * MINUTE).toISOString();
const placeholder = (name: string) => `${APP_BASE}static/images/placeholders/${name}.svg`;

/** Mock: ID квартир из mock_data.json, чтобы /listing/{id} открывался */
const SEED: AppNotification[] = [
  {
    id: 'mock-n1',
    type: 'new_listing',
    created_at: ago(5),
    is_read: false,
    listing: {
      id: '4',
      title: {
        ka: 'ერთოთახიანი ბინა ვაკეში',
        ru: 'Однокомнатная квартира в Ваке',
        en: 'One-room apartment in Vake',
      },
      price: 950,
      currency: 'GEL',
      image: placeholder('kitchen'),
    },
    search_id: 'mock-1',
    search_name: 'Vake · ≤ 2 000 ₾',
  },
  {
    id: 'mock-n2',
    type: 'price_drop',
    created_at: ago(3 * 60),
    is_read: false,
    listing: {
      id: '1',
      title: {
        ka: 'მყუდრო ბინა საბურთალოზე',
        ru: 'Уютная квартира в Сабуртало',
        en: 'Cozy apartment in Saburtalo',
      },
      price: 650,
      currency: 'GEL',
      image: placeholder('living-room'),
    },
    old_price: 750,
  },
  {
    id: 'mock-n3',
    type: 'new_listing',
    created_at: ago(26 * 60),
    is_read: false,
    listing: {
      id: '2',
      title: {
        ka: 'ბინა საბურთალოზე, ევროპის სკვერთან',
        ru: 'Квартира в Сабуртало, у Парка Европы',
        en: 'Apartment in Saburtalo, near Europe Square',
      },
      price: 1150,
      currency: 'GEL',
      image: placeholder('bedroom'),
    },
    search_id: 'mock-2',
    search_name: 'Saburtalo · 800–1 500 ₾',
  },
  {
    id: 'mock-n4',
    type: 'system',
    created_at: ago(3 * 24 * 60),
    is_read: true,
    text: {
      ka: 'კეთილი იყოს თქვენი მობრძანება Bina.ai-ში! შეინახეთ ძიება და ახალ ბინებს პირველებს გამოგიგზავნით.',
      ru: 'Добро пожаловать в Bina.ai! Сохраните поиск — и мы первыми пришлём новые квартиры.',
      en: 'Welcome to Bina.ai! Save a search and we will send you new apartments first.',
    },
  },
  {
    id: 'mock-n5',
    type: 'price_drop',
    created_at: ago(10 * 24 * 60),
    is_read: true,
    listing: {
      id: '5',
      title: { ka: 'ბინა ვერაზე', ru: 'Квартира в Вере', en: 'Apartment in Vera' },
      price: 1500,
      currency: 'GEL',
      image: null,
    },
    old_price: 1700,
  },
];

// Режим выбирается один раз за сессию по первому ответу бэкенда
let localMode = false;

/** 404 — эндпоинта ещё нет, 0 — нет сети: переходим на mock */
function shouldFallback(error: unknown): boolean {
  return error instanceof ApiError && (error.isNotFound || error.status === 0);
}

function toApiError(error: unknown): ApiError {
  return error instanceof ApiError ? error : new ApiError(0, String(error));
}

/* ---------- mock: прочитанность в localStorage ---------- */

function loadReadIds(): Set<string> {
  try {
    const value: unknown = JSON.parse(window.localStorage.getItem(READ_KEY) ?? '[]');
    return new Set(
      Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [],
    );
  } catch {
    // localStorage недоступен (приватный режим) или повреждён
    return new Set();
  }
}

function saveReadIds(ids: Set<string>): void {
  try {
    window.localStorage.setItem(READ_KEY, JSON.stringify([...ids]));
  } catch {
    // Не удалось сохранить — останется до перезагрузки страницы
  }
}

function localItems(): AppNotification[] {
  const read = loadReadIds();
  return SEED.map((item) => ({ ...item, is_read: item.is_read || read.has(item.id) }));
}

function localUnreadCount(): number {
  return localItems().filter((item) => !item.is_read).length;
}

function localPage(filter: NotificationFilter, page: number): NotificationsPage {
  const all = localItems();
  const filtered = filter === 'unread' ? all.filter((item) => !item.is_read) : all;
  return {
    items: filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE),
    total: filtered.length,
    page,
    pages: Math.max(1, Math.ceil(filtered.length / PER_PAGE)),
    unread_count: all.filter((item) => !item.is_read).length,
  };
}

function localMarkRead(ids: string[]): void {
  const read = loadReadIds();
  ids.forEach((id) => read.add(id));
  saveReadIds(read);
}

/** Страница ленты: с бэкенда или (404 / нет сети) из mock */
async function fetchPage(
  filter: NotificationFilter,
  page: number,
  signal?: AbortSignal,
): Promise<NotificationsPage> {
  if (localMode) return localPage(filter, page);
  const query = new URLSearchParams({ filter, page: String(page), per_page: String(PER_PAGE) });
  try {
    return await apiGet<NotificationsPage>(`${API_PATH}?${query}`, signal);
  } catch (error) {
    if (!shouldFallback(error)) throw error;
    localMode = true;
    return localPage(filter, page);
  }
}

/* ---------- общий счётчик непрочитанных (шапка + страница) ---------- */

let unreadCount = 0;
const listeners = new Set<() => void>();

function setUnreadCount(value: number): void {
  const next = Math.max(0, value);
  if (next === unreadCount) return;
  unreadCount = next;
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): number {
  return unreadCount;
}

async function refreshUnreadCount(): Promise<void> {
  if (localMode) {
    setUnreadCount(localUnreadCount());
    return;
  }
  try {
    const { count } = await apiGet<UnreadCountResponse>(`${API_PATH}/unread-count`);
    setUnreadCount(count);
  } catch (error) {
    if (shouldFallback(error)) {
      localMode = true;
      setUnreadCount(localUnreadCount());
    } else if (error instanceof ApiError && error.isUnauthorized) {
      setUnreadCount(0);
    }
    // Остальные ошибки — оставляем прошлое число до следующей попытки
  }
}

/**
 * Число непрочитанных для колокольчика в шапке. Обновляется раз в минуту и при возврате
 * на вкладку; у гостя всегда 0.
 */
export function useUnreadNotifications(): number {
  const count = useSyncExternalStore(subscribe, getSnapshot);
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    if (!isAuthenticated) {
      setUnreadCount(0);
      return;
    }
    const refresh = () => {
      // Скрытая вкладка / свёрнутый Mini App — не тратим запросы
      if (document.visibilityState === 'visible') void refreshUnreadCount();
    };
    refresh();
    const timer = window.setInterval(refresh, POLL_INTERVAL);
    document.addEventListener('visibilitychange', refresh);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', refresh);
    };
  }, [isAuthenticated]);

  return isAuthenticated ? count : 0;
}

/* ---------- лента для страницы /notifications ---------- */

interface FeedState {
  items: AppNotification[];
  page: number;
  pages: number;
  loading: boolean;
  loadingMore: boolean;
  error?: ApiError;
}

const INITIAL: FeedState = { items: [], page: 1, pages: 1, loading: true, loadingMore: false };

/**
 * Лента уведомлений: фильтр all/unread, «Показать ещё», отметка прочитанного.
 * Ошибки действий показываются toast'ом, интерфейс откатывается.
 */
export function useNotificationFeed() {
  const { t } = useI18n();
  const showToast = useToast();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const unread = useSyncExternalStore(subscribe, getSnapshot);
  const [filter, setFilter] = useState<NotificationFilter>('all');
  const [state, setState] = useState<FeedState>(INITIAL);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    // Гостю запрос не нужен — бэкенд всё равно ответит 401
    if (!isAuthenticated) return;
    const controller = new AbortController();
    setState(INITIAL);
    fetchPage(filter, 1, controller.signal).then(
      (data) => {
        setState({ ...INITIAL, items: data.items, pages: data.pages, loading: false });
        setUnreadCount(data.unread_count);
      },
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setState({ ...INITIAL, loading: false, error: toApiError(error) });
      },
    );
    return () => controller.abort();
  }, [isAuthenticated, filter, attempt]);

  const reload = useCallback(() => setAttempt((value) => value + 1), []);

  const loadMore = useCallback(async () => {
    const next = state.page + 1;
    if (state.loadingMore || next > state.pages) return;
    setState((current) => ({ ...current, loadingMore: true }));
    try {
      const data = await fetchPage(filter, next);
      setState((current) => {
        // Уведомления, которые уже есть (сдвиг страниц после новых), не дублируем
        const known = new Set(current.items.map((item) => item.id));
        return {
          ...current,
          items: [...current.items, ...data.items.filter((item) => !known.has(item.id))],
          page: next,
          pages: data.pages,
          loadingMore: false,
        };
      });
      setUnreadCount(data.unread_count);
    } catch {
      setState((current) => ({ ...current, loadingMore: false }));
      showToast(t.notifications.error, 'error');
      haptic('error');
    }
  }, [state.page, state.pages, state.loadingMore, filter, showToast, t]);

  const fail = useCallback(
    (before: FeedState, count: number) => {
      setState(before);
      setUnreadCount(count);
      showToast(t.notifications.error, 'error');
      haptic('error');
    },
    [showToast, t],
  );

  /** Отметить прочитанным; во вкладке «Непрочитанные» карточка сразу исчезает */
  const markRead = useCallback(
    async (id: string): Promise<void> => {
      const target = state.items.find((item) => item.id === id);
      if (!target || target.is_read) return;
      const before = state;
      const countBefore = unreadCount;
      setState((current) => ({
        ...current,
        items:
          filter === 'unread'
            ? current.items.filter((item) => item.id !== id)
            : current.items.map((item) => (item.id === id ? { ...item, is_read: true } : item)),
      }));
      setUnreadCount(countBefore - 1);
      if (localMode) {
        localMarkRead([id]);
        return;
      }
      try {
        await apiPost(`${API_PATH}/${encodeURIComponent(id)}/read`);
      } catch {
        fail(before, countBefore);
      }
    },
    [state, filter, fail],
  );

  const markAllRead = useCallback(async (): Promise<boolean> => {
    const before = state;
    const countBefore = unreadCount;
    setState((current) => ({
      ...current,
      items: filter === 'unread' ? [] : current.items.map((item) => ({ ...item, is_read: true })),
    }));
    setUnreadCount(0);
    if (localMode) {
      localMarkRead(SEED.map((item) => item.id));
      return true;
    }
    try {
      await apiPost(`${API_PATH}/read-all`);
      return true;
    } catch {
      fail(before, countBefore);
      return false;
    }
  }, [state, filter, fail]);

  // Гость или 401 от бэкенда (вне Telegram initData нет) — нужен вход через Telegram
  const unauthorized = (!authLoading && !isAuthenticated) || Boolean(state.error?.isUnauthorized);

  return {
    items: state.items,
    unreadCount: unread,
    filter,
    setFilter,
    hasMore: state.page < state.pages,
    loadMore,
    loadingMore: state.loadingMore,
    loading: authLoading || (isAuthenticated && state.loading),
    error: state.error?.isUnauthorized ? undefined : state.error,
    unauthorized,
    reload,
    markRead,
    markAllRead,
  };
}
