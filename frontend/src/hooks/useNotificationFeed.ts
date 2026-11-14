import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';
import { ApiError, apiGet, apiPost } from '../api/client';
import type { AppNotification, NotificationsPage, UnreadCountResponse } from '../api/types';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

// Лента уведомлений (новые квартиры по сохранённым поискам, снижение цены в избранном) —
// только с сервера (/api/notifications). Нет сети — ошибка с «Повторить», без выдуманных
// уведомлений.
//
// Имя useNotifications.ts занято настройкой «Уведомления» в профиле.
const API_PATH = '/api/notifications';
const PER_PAGE = 20;
const POLL_INTERVAL = 60_000;

export type NotificationFilter = 'all' | 'unread';

// Здесь раньше жил демо-режим (прочитанность в браузере) — стираем, что от него осталось
try {
  window.localStorage.removeItem('bina:notifications_read');
} catch {
  // localStorage недоступен (приватный режим) — стирать нечего
}

function toApiError(error: unknown): ApiError {
  return error instanceof ApiError ? error : new ApiError(0, String(error));
}

function fetchPage(
  filter: NotificationFilter,
  page: number,
  signal?: AbortSignal,
): Promise<NotificationsPage> {
  const query = new URLSearchParams({ filter, page: String(page), per_page: String(PER_PAGE) });
  return apiGet<NotificationsPage>(`${API_PATH}?${query}`, signal);
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
  try {
    const { count } = await apiGet<UnreadCountResponse>(`${API_PATH}/unread-count`);
    setUnreadCount(count);
  } catch (error) {
    if (error instanceof ApiError && error.isUnauthorized) setUnreadCount(0);
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

/**
 * То же число без своих запросов — для плитки главного меню: счётчик уже обновляет
 * шапка (useUnreadNotifications), она есть на каждой странице.
 */
export function useUnreadCount(): number {
  return useSyncExternalStore(subscribe, getSnapshot);
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
