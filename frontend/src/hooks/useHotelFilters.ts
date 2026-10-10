import { useCallback, useMemo } from 'react';
import type { HotelFilters } from '../api/types';
import {
  HOTEL_FILTER_KEYS,
  HOTEL_SORT_KEY,
  hotelFilterEntries,
  parseHotelFilters,
  parseHotelSort,
  type HotelSort,
} from '../lib/hotelFilters';
import { useUrlParams } from './useUrlParams';

/** Записать фильтры в параметры адреса вместо прежних; страница сбрасывается на первую */
function writeFilters(params: URLSearchParams, filters: HotelFilters): void {
  HOTEL_FILTER_KEYS.forEach((key) => params.delete(key));
  hotelFilterEntries(filters).forEach(([key, value]) => params.set(key, value));
  params.delete('page');
}

/**
 * Фильтры, сортировка и страница поиска гостиниц живут в адресе:
 * ?kind=hotel,hostel&guests=2&price_min=..&price_max=..&stars=4&amenities=wifi,parking&sort=..&page=..
 * Город в адрес не входит: он общий для приложения (useCity)
 */
export function useHotelFilters() {
  const { search, update } = useUrlParams();
  // Новый объект только при изменении адреса — на filters можно опираться в эффектах
  const filters = useMemo(() => parseHotelFilters(new URLSearchParams(search)), [search]);
  const sort = parseHotelSort(new URLSearchParams(search).get(HOTEL_SORT_KEY));
  const page = Math.max(
    1,
    Number.parseInt(new URLSearchParams(search).get('page') ?? '1', 10) || 1,
  );

  /** Изменить часть фильтров (undefined — убрать фильтр) */
  const setFilters = useCallback(
    (patch: HotelFilters) => {
      // Фильтры — не отдельные записи истории: «Назад» уводит со страницы
      update((params) => writeFilters(params, { ...parseHotelFilters(params), ...patch }), true);
    },
    [update],
  );

  /** Заменить все фильтры разом («Показать» в окне фильтров) */
  const replaceFilters = useCallback(
    (next: HotelFilters) => update((params) => writeFilters(params, next), true),
    [update],
  );

  /** Сортировка остаётся */
  const resetFilters = useCallback(
    () => update((params) => writeFilters(params, {}), true),
    [update],
  );

  /** Сортировка; undefined — порядок сервера по умолчанию. Страница — первая */
  const setSort = useCallback(
    (next: HotelSort | undefined) => {
      update(
        (params) => {
          if (next) params.set(HOTEL_SORT_KEY, next);
          else params.delete(HOTEL_SORT_KEY);
          params.delete('page');
        },
        true,
        true,
      );
    },
    [update],
  );

  const setPage = useCallback(
    (next: number) => {
      update((params) => {
        if (next > 1) params.set('page', String(next));
        else params.delete('page');
      }, false);
    },
    [update],
  );

  return { filters, sort, page, setFilters, replaceFilters, resetFilters, setSort, setPage };
}
