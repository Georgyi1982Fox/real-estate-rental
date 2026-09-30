import { useCallback, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { SearchFilters } from '../api/types';
import { FILTER_KEYS, filterEntries, parseFilters } from '../lib/searchFilters';

/** Записать фильтры в параметры адреса вместо прежних; страница сбрасывается на первую */
function writeFilters(params: URLSearchParams, filters: SearchFilters): void {
  FILTER_KEYS.forEach((key) => params.delete(key));
  filterEntries(filters).forEach(([key, value]) => params.set(key, value));
  params.delete('page');
}

/**
 * Фильтры и страница главной живут в адресе:
 * ?district=<id>,<id>&min_price=..&max_price=..&rooms=..&page=..
 * Такую ссылку можно открыть заново или сохранить как поиск.
 */
export function useSearchFilters() {
  const { search } = useLocation();
  const navigate = useNavigate();
  // Новый объект только при изменении адреса — на filters можно опираться в эффектах
  const filters = useMemo(() => parseFilters(new URLSearchParams(search)), [search]);
  const page = Math.max(
    1,
    Number.parseInt(new URLSearchParams(search).get('page') ?? '1', 10) || 1,
  );

  /**
   * Изменить параметры адреса. setSearchParams из React Router кодирует запятую как %2C,
   * а районы в адресе должны читаться: ?district=vake,saburtalo
   */
  const update = useCallback(
    (change: (params: URLSearchParams) => void, replace: boolean) => {
      const params = new URLSearchParams(search);
      change(params);
      const next = params.toString().replace(/%2C/gi, ',');
      navigate({ search: next ? `?${next}` : '' }, { replace });
    },
    [search, navigate],
  );

  /** Изменить часть фильтров (undefined — убрать фильтр) */
  const setFilters = useCallback(
    (patch: SearchFilters) => {
      // Фильтры — не отдельные записи истории: «Назад» уводит со страницы
      update((params) => writeFilters(params, { ...parseFilters(params), ...patch }), true);
    },
    [update],
  );

  /** Заменить все фильтры разом («Показать» в окне фильтров) */
  const replaceFilters = useCallback(
    (next: SearchFilters) => update((params) => writeFilters(params, next), true),
    [update],
  );

  const resetFilters = useCallback(() => replaceFilters({}), [replaceFilters]);

  const setPage = useCallback(
    (next: number) => {
      update((params) => {
        if (next > 1) params.set('page', String(next));
        else params.delete('page');
      }, false);
    },
    [update],
  );

  return { filters, page, setFilters, replaceFilters, resetFilters, setPage };
}
