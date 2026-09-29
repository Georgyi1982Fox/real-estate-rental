import { useCallback, useEffect, useState } from 'react';
import { ApiError, apiDelete, apiGet, apiPatch, apiPost } from '../api/client';
import type {
  CreateSavedSearchRequest,
  ListResponse,
  SavedSearch,
  SearchFilters,
  UpdateSavedSearchRequest,
} from '../api/types';
import { sameFilters } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import { showPremiumPrompt } from './usePremiumPrompt';

// Сохранённые поиски. Сначала — бэкенд /api/searches. Пока его нет (404) или нет сети,
// работаем с mock-данными в localStorage: интерфейс полностью рабочий, а когда
// бэкенд появится, хук перейдёт на него без переделок.
const API_PATH = '/api/searches';
const STORAGE_KEY = 'bina:saved_searches';

/** Mock для первого запуска. name пустой — страница покажет фильтры словами на языке интерфейса */
const SEED: SavedSearch[] = [
  {
    id: 'mock-1',
    name: '',
    filters: { district: 'vake', rooms: 2, max_price: 2000 },
    notify: true,
    new_count: 5,
    created_at: '2026-09-20T10:00:00Z',
  },
  {
    id: 'mock-2',
    name: '',
    filters: { district: 'saburtalo', min_price: 800, max_price: 1500 },
    notify: true,
    new_count: 0,
    created_at: '2026-09-18T10:00:00Z',
  },
  {
    id: 'mock-3',
    name: '',
    filters: { rooms: 3, min_price: 1500 },
    notify: false,
    new_count: 2,
    created_at: '2026-09-15T10:00:00Z',
  },
];

// Режим выбирается один раз за сессию по первому ответу GET /api/searches
let localMode = false;

/** 404 — эндпоинта ещё нет, 0 — нет сети: переходим на mock */
function shouldFallback(error: unknown): boolean {
  return error instanceof ApiError && (error.isNotFound || error.status === 0);
}

function isSavedSearch(value: unknown): value is SavedSearch {
  if (typeof value !== 'object' || value === null) return false;
  const item = value as Partial<SavedSearch>;
  return typeof item.id === 'string' && typeof item.filters === 'object' && item.filters !== null;
}

function loadLocal(): SavedSearch[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === null) return SEED;
    const value: unknown = JSON.parse(raw);
    return Array.isArray(value) ? value.filter(isSavedSearch) : SEED;
  } catch {
    // localStorage недоступен (приватный режим) или повреждён
    return SEED;
  }
}

function saveLocal(searches: SavedSearch[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(searches));
  } catch {
    // Не удалось сохранить — останется до перезагрузки страницы
  }
}

function localId(): string {
  return typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

interface State {
  searches: SavedSearch[];
  loading: boolean;
  error?: ApiError;
}

/**
 * Сохранённые поиски текущего пользователя. Методы сами показывают toast ошибки и
 * возвращают результат (true / созданный поиск) или null/false при неудаче.
 */
export function useSavedSearches() {
  const { t } = useI18n();
  const showToast = useToast();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [state, setState] = useState<State>({ searches: [], loading: true });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    // Гостю запрос не нужен — бэкенд всё равно ответит 401
    if (!isAuthenticated) return;
    if (localMode) {
      setState({ searches: loadLocal(), loading: false });
      return;
    }
    const controller = new AbortController();
    setState((current) => ({ ...current, loading: true, error: undefined }));
    apiGet<ListResponse<SavedSearch>>(API_PATH, controller.signal).then(
      ({ items }) => setState({ searches: items, loading: false }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        if (shouldFallback(error)) {
          localMode = true;
          setState({ searches: loadLocal(), loading: false });
          return;
        }
        setState({
          searches: [],
          loading: false,
          error: error instanceof ApiError ? error : new ApiError(0, String(error)),
        });
      },
    );
    return () => controller.abort();
  }, [isAuthenticated, attempt]);

  const reload = useCallback(() => setAttempt((value) => value + 1), []);

  /** Изменить список; в mock-режиме сразу сохраняем в localStorage */
  const update = useCallback((change: (searches: SavedSearch[]) => SavedSearch[]) => {
    setState((current) => {
      const searches = change(current.searches);
      if (localMode) saveLocal(searches);
      return { ...current, searches };
    });
  }, []);

  const fail = useCallback(() => {
    showToast(t.searches.error, 'error');
    haptic('error');
  }, [showToast, t]);

  const replace = useCallback(
    (next: SavedSearch) =>
      update((list) => list.map((item) => (item.id === next.id ? next : item))),
    [update],
  );

  const save = useCallback(
    async (filters: SearchFilters, name?: string): Promise<SavedSearch | null> => {
      const body: CreateSavedSearchRequest = { filters, notify: true };
      if (name) body.name = name;
      try {
        const created: SavedSearch = localMode
          ? {
              id: localId(),
              name: name ?? '',
              filters,
              notify: true,
              new_count: 0,
              created_at: new Date().toISOString(),
            }
          : await apiPost<SavedSearch>(API_PATH, body);
        update((list) => [created, ...list]);
        return created;
      } catch (error) {
        // Лимит бесплатного тарифа — не ошибка, а предложение Premium
        if (error instanceof ApiError && error.isPaymentRequired) {
          haptic('warning');
          showPremiumPrompt('searches');
        } else {
          fail();
        }
        return null;
      }
    },
    [update, fail],
  );

  /** PATCH /api/searches/{id}; в mock — просто изменить запись */
  const patch = useCallback(
    async (search: SavedSearch, body: UpdateSavedSearchRequest): Promise<SavedSearch> =>
      localMode
        ? { ...search, ...body }
        : apiPatch<SavedSearch>(`${API_PATH}/${encodeURIComponent(search.id)}`, body),
    [],
  );

  const rename = useCallback(
    async (id: string, name: string): Promise<boolean> => {
      const search = state.searches.find((item) => item.id === id);
      if (!search) return false;
      try {
        replace(await patch(search, { name }));
        return true;
      } catch {
        fail();
        return false;
      }
    },
    [state.searches, patch, replace, fail],
  );

  const toggleNotify = useCallback(
    async (id: string): Promise<boolean> => {
      const search = state.searches.find((item) => item.id === id);
      if (!search) return false;
      const notify = !search.notify;
      // Переключатель отвечает сразу, при ошибке возвращаем как было
      replace({ ...search, notify });
      try {
        replace(await patch(search, { notify }));
        return true;
      } catch {
        replace(search);
        fail();
        return false;
      }
    },
    [state.searches, patch, replace, fail],
  );

  const remove = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        if (!localMode) await apiDelete(`${API_PATH}/${encodeURIComponent(id)}`);
        update((list) => list.filter((item) => item.id !== id));
        return true;
      } catch {
        fail();
        return false;
      }
    },
    [update, fail],
  );

  /**
   * Пользователь открыл поиск — новые квартиры просмотрены. На бэкенде счётчик
   * сбрасывает сервер, здесь — только в интерфейсе (в mock — и в localStorage).
   */
  const markSeen = useCallback(
    (id: string) =>
      update((list) => list.map((item) => (item.id === id ? { ...item, new_count: 0 } : item))),
    [update],
  );

  /** Уже сохранённый поиск с такими же фильтрами */
  const findByFilters = useCallback(
    (filters: SearchFilters) => state.searches.find((item) => sameFilters(item.filters, filters)),
    [state.searches],
  );

  // Гость или 401 от бэкенда (вне Telegram initData нет) — нужен вход через Telegram
  const unauthorized = (!authLoading && !isAuthenticated) || Boolean(state.error?.isUnauthorized);

  return {
    searches: state.searches,
    loading: authLoading || (isAuthenticated && state.loading),
    error: state.error?.isUnauthorized ? undefined : state.error,
    unauthorized,
    reload,
    save,
    rename,
    toggleNotify,
    remove,
    markSeen,
    findByFilters,
  };
}
