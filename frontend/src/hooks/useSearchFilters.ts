import { useCallback, useEffect, useMemo } from 'react';
import type { RentPeriod, SearchFilters } from '../api/types';
import {
  cleanQuery,
  FILTER_KEYS,
  filterDistricts,
  filterEntries,
  parseFilters,
  parseSort,
  QUERY_KEY,
  SMART_SORT,
  SORT_KEY,
  type SortOrder,
} from '../lib/searchFilters';
import { cityParam, saveCity } from './useCity';
import { useUrlParams } from './useUrlParams';

/** Записать фильтры в параметры адреса вместо прежних; страница сбрасывается на первую */
function writeFilters(params: URLSearchParams, filters: SearchFilters): void {
  FILTER_KEYS.forEach((key) => params.delete(key));
  // Текст поиска (q) в адресе меняет только setQuery
  filterEntries({ ...filters, q: undefined }).forEach(([key, value]) => params.set(key, value));
  params.delete('page');
}

/**
 * Поиск, фильтры, сортировка и страница ленты живут в адресе:
 * ?q=<текст>&district=<id>,<id>&min_price=..&rooms=..&features=<код>,<код>&owner_only=true&rent_period=daily&sort=..&page=..
 * Такую ссылку можно открыть заново или сохранить как поиск.
 *
 * Город в фильтры страницы не входит: он общий для приложения (useCity). Ссылка с
 * ?city=batumi (или ?city=all — «Вся Грузия») переключает город и запоминает его,
 * после чего city из адреса убирается; без city действует запомненный город.
 */
export function useSearchFilters() {
  const { search, update } = useUrlParams();
  // Новый объект только при изменении адреса — на filters можно опираться в эффектах
  const { filters, urlCity } = useMemo(() => {
    const { city, ...rest } = parseFilters(new URLSearchParams(search));
    return { filters: rest, urlCity: city };
  }, [search]);
  const query = cleanQuery(new URLSearchParams(search).get(QUERY_KEY));
  const sort = parseSort(new URLSearchParams(search).get(SORT_KEY));
  // Ссылка из бота: ?q=…&sort=smart открывает поиск по смыслу, даже если он был выключен
  const smartLink = new URLSearchParams(search).get(SORT_KEY) === SMART_SORT;
  const page = Math.max(
    1,
    Number.parseInt(new URLSearchParams(search).get('page') ?? '1', 10) || 1,
  );

  // Город из ссылки становится выбранным; в адресе он больше не нужен
  useEffect(() => {
    if (urlCity === undefined) return;
    saveCity(cityParam(urlCity));
    update((params) => params.delete('city'), true, true);
  }, [urlCity, update]);

  /** Выбрать город (undefined — «Вся Грузия»): районы прежнего города сбрасываются */
  const setCity = useCallback(
    (city: string | undefined) => {
      saveCity(city);
      update(
        (params) =>
          writeFilters(params, {
            ...parseFilters(params),
            district: undefined,
            districts: undefined,
            city: undefined,
          }),
        true,
        true,
      );
    },
    [update],
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

  /** «Сбросить фильтры» убирает и текст поиска; сортировка и срок аренды остаются */
  const resetFilters = useCallback(
    () =>
      update((params) => {
        writeFilters(params, { rent_period: parseFilters(params).rent_period });
        params.delete(QUERY_KEY);
      }, true),
    [update],
  );

  /** «Помесячно / Посуточно»: цена за месяц и за сутки несравнимы — фильтр цены сбрасывается */
  const setRentPeriod = useCallback(
    (period: RentPeriod) => {
      update(
        (params) =>
          writeFilters(params, {
            ...parseFilters(params),
            rent_period: period,
            min_price: undefined,
            max_price: undefined,
          }),
        true,
        true,
      );
    },
    [update],
  );

  /**
   * Поиск по словам; пустая строка убирает q. Фильтры остаются, страница — первая.
   * dropSort — новый текст ищем по смыслу, выбранная раньше сортировка ему уступает
   */
  const setQuery = useCallback(
    (text: string, dropSort = false) => {
      update(
        (params) => {
          const next = cleanQuery(text);
          if (next) params.set(QUERY_KEY, next);
          else params.delete(QUERY_KEY);
          // sort=smart из ссылки относится только к её тексту
          if (dropSort || params.get(SORT_KEY) === SMART_SORT) params.delete(SORT_KEY);
          params.delete('page');
        },
        true,
        // Куда прокрутить после поиска, решает страница
        true,
      );
    },
    [update],
  );

  /** Район из подсказок поиска: добавляется к фильтру районов, текст поиска убирается */
  const addDistrict = useCallback(
    (id: string) => {
      update((params) => {
        const current = parseFilters(params);
        writeFilters(params, { ...current, districts: [...filterDistricts(current), id] });
        params.delete(QUERY_KEY);
      }, true);
    },
    [update],
  );

  /** Сортировка; undefined — порядок сервера по умолчанию. Страница — первая */
  const setSort = useCallback(
    (next: SortOrder | undefined) => {
      update(
        (params) => {
          if (next) params.set(SORT_KEY, next);
          else params.delete(SORT_KEY);
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

  return {
    filters,
    /** Город из ссылки, пока он не стал выбранным: в этом рендере он важнее запомненного */
    urlCity,
    query,
    sort,
    smartLink,
    page,
    setFilters,
    replaceFilters,
    resetFilters,
    setCity,
    setRentPeriod,
    setQuery,
    addDistrict,
    setSort,
    setPage,
  };
}
