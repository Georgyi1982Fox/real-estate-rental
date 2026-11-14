import { useCallback, useEffect, useState } from 'react';
import { ApiError, apiDelete, apiGet, apiPatch, apiPost } from '../api/client';
import type {
  CreateSavedSearchRequest,
  ListResponse,
  SavedSearch,
  SearchFilters,
  UpdateSavedSearchRequest,
} from '../api/types';
import {
  cleanFilters,
  fromSavedFilters,
  sameFilters,
  toSavedFilters,
} from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import { showPremiumPrompt } from './usePremiumPrompt';

// Сохранённые поиски — только на сервере (/api/searches): по ним бот присылает новые
// квартиры. Нет сети — обычная ошибка с «Повторить», а не поиск, сохранённый только
// на этом устройстве.
const API_PATH = '/api/searches';

// Здесь раньше жил демо-режим (поиски только в браузере) — стираем, что от него осталось
try {
  window.localStorage.removeItem('bina:saved_searches');
} catch {
  // localStorage недоступен (приватный режим) — стирать нечего
}

/** Сервер отдаёт незаданные фильтры как null — в приложении таких полей просто нет */
function normalize(search: SavedSearch): SavedSearch {
  return { ...search, filters: fromSavedFilters(cleanFilters(search.filters)) };
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
    const controller = new AbortController();
    setState((current) => ({ ...current, loading: true, error: undefined }));
    apiGet<ListResponse<SavedSearch>>(API_PATH, controller.signal).then(
      ({ items }) => setState({ searches: items.map(normalize), loading: false }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
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

  const update = useCallback((change: (searches: SavedSearch[]) => SavedSearch[]) => {
    setState((current) => ({ ...current, searches: change(current.searches) }));
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
    async (searchFilters: SearchFilters, name?: string): Promise<SavedSearch | null> => {
      // Все выбранные фильтры и текст поиска; один район — поле district, несколько — districts
      const filters = toSavedFilters(searchFilters);
      const body: CreateSavedSearchRequest = { filters, notify: true };
      if (name) body.name = name;
      try {
        const created = normalize(await apiPost<SavedSearch>(API_PATH, body));
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

  /** PATCH /api/searches/{id} */
  const patch = useCallback(
    async (search: SavedSearch, body: UpdateSavedSearchRequest): Promise<SavedSearch> =>
      normalize(await apiPatch<SavedSearch>(`${API_PATH}/${encodeURIComponent(search.id)}`, body)),
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
        await apiDelete(`${API_PATH}/${encodeURIComponent(id)}`);
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
   * Пользователь открыл поиск — новые квартиры просмотрены. Счётчик на сервере
   * сбрасывает сам сервер, здесь — только в интерфейсе.
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
