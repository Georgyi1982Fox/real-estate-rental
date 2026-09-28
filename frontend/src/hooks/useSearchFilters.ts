import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { SearchFilters } from '../api/types';
import { FILTER_KEYS, parseFilters } from '../lib/searchFilters';

/**
 * Фильтры и страница главной живут в адресе: ?district=..&min_price=..&max_price=..&rooms=..&page=..
 * Такую ссылку можно открыть заново или сохранить как поиск.
 */
export function useSearchFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.toString();
  // Новый объект только при изменении адреса — на filters можно опираться в эффектах
  const filters = useMemo(() => parseFilters(new URLSearchParams(query)), [query]);
  const page = Math.max(1, Number.parseInt(searchParams.get('page') ?? '1', 10) || 1);

  /** Изменить часть фильтров (undefined — убрать фильтр); страница сбрасывается на первую */
  const setFilters = useCallback(
    (patch: SearchFilters) => {
      setSearchParams(
        (params) => {
          for (const key of FILTER_KEYS) {
            if (!(key in patch)) continue;
            const value = patch[key];
            if (value === undefined || value === '') params.delete(key);
            else params.set(key, String(value));
          }
          params.delete('page');
          return params;
        },
        // Каждая цифра цены — не отдельная запись истории: «Назад» уводит со страницы
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const resetFilters = useCallback(() => {
    setSearchParams(
      (params) => {
        FILTER_KEYS.forEach((key) => params.delete(key));
        params.delete('page');
        return params;
      },
      { replace: true },
    );
  }, [setSearchParams]);

  const setPage = useCallback(
    (next: number) => {
      setSearchParams((params) => {
        if (next > 1) params.set('page', String(next));
        else params.delete('page');
        return params;
      });
    },
    [setSearchParams],
  );

  return { filters, page, setFilters, resetFilters, setPage };
}
