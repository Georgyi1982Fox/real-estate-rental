import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ListingsPage } from '../api/types';
import CityPicker from '../components/CityPicker';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import FilterButton from '../components/FilterButton';
import FilterChips from '../components/FilterChips';
import CompareBar from '../components/CompareBar';
import FilterModal from '../components/FilterModal';
import Icon from '../components/Icon';
import ListingCard from '../components/ListingCard';
import Pagination from '../components/Pagination';
import RentPeriodToggle from '../components/RentPeriodToggle';
import SaveSearchButton from '../components/SaveSearchButton';
import SearchBar from '../components/SearchBar';
import type { MapFallback } from '../components/SearchMap';
import SearchViewToggle from '../components/SearchViewToggle';
import Skeleton from '../components/Skeleton';
import SmartSearchToggle from '../components/SmartSearchToggle';
import SortSelect from '../components/SortSelect';
import { useApi } from '../hooks/useApi';
import { cityParam, useCity } from '../hooks/useCity';
import { useCityDistricts, useDistricts } from '../hooks/useDistricts';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useSearchFilters } from '../hooks/useSearchFilters';
import { saveSmartSearch, useSmartSearch } from '../hooks/useSmartSearch';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { fill, fillVars, plural, tr } from '../lib/format';
import { lazyPage } from '../lib/lazyPage';
import { groupByBuilding } from '../lib/mapGroups';
import {
  canSmartSearch,
  cityCodes,
  countFilters,
  filterDistricts,
  hasFilters,
  isDaily,
  searchToQuery,
  SMART_SORT,
  withQuery,
} from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { RENT_PATH } from '../lib/paths';
import { useI18n } from '../providers/I18nProvider';

const LISTINGS_PER_PAGE = 6;
/** На карте — больше квартир на странице (FRONTEND-056) */
const MAP_PER_PAGE = 50;
/** Нет ни одной точки: центр выбранного города, а если город не один — вся Грузия */
const CITY_ZOOM = 12;
const GEORGIA: MapFallback = { latitude: 42.2, longitude: 43.5, zoom: 7 };
// Высота и отступы прокрутки — в main.css (.search-page__map): от высоты экрана и нижнего меню
const MAP_BOX_CLASS = 'search-page__map relative w-full';
const MAP_SKELETON_CLASS =
  'h-full w-full animate-pulse rounded-[var(--radius-lg)] bg-[var(--surface-hover)]';
// Leaflet (~150 КБ) — только когда открыли карту; в основной index-*.js не попадает
const SearchMap = lazyPage(() => import('../components/SearchMap'));
const SKELETON_COUNT = 4;
const GRID_CLASS = 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';
const PRIMARY_BUTTON_CLASS =
  'inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]';

/** Лента объявлений с поиском, фильтрами и страницами: помесячная или посуточная аренда */
export default function SearchPage() {
  const { lang, t } = useI18n();
  const ht = t.home;
  const {
    filters,
    urlCity,
    query,
    sort,
    smartLink,
    page,
    view,
    setFilters,
    replaceFilters,
    resetFilters,
    setCity,
    setRentPeriod,
    setQuery,
    addDistrict,
    setSort,
    setPage,
    setView,
  } = useSearchFilters();
  const isMap = view === 'map';
  const mt = ht.map;
  const [filtersOpen, setFiltersOpen] = useState(false);
  const openFilters = useCallback(() => setFiltersOpen(true), []);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeFilters = useCallback(() => setFiltersOpen(false), []);
  const resultsRef = useRef<HTMLElement>(null);
  // Включили карту или другую её страницу — карта встаёт на экран целиком
  const mapRef = useRef<HTMLDivElement>(null);
  const scrollToMap = useRef(false);
  const cities = useCity();
  // Город из ссылки (?city=…) важнее запомненного; undefined — «Вся Грузия»
  const city = urlCity === undefined ? cities.city : cityParam(urlCity);
  // «По смыслу»: нужен текст из 3+ букв. Включён по ссылке (sort=smart) или по запомненному
  // выбору, пока в адресе нет обычной сортировки
  const smartPreferred = useSmartSearch();
  const smartAvailable = canSmartSearch(query);
  const smart = smartAvailable && (smartLink || (sort === undefined && smartPreferred));
  const searchQuery = searchToQuery({ ...filters, city }, query, smart ? SMART_SORT : sort);
  // Поиск сохраняется целиком: город + фильтры + текст из строки поиска (без сортировки).
  // Сайт не передаём: сохранённые поиски его ещё не хранят
  const savedFilters = useMemo(
    () => withQuery({ ...filters, source: undefined, city }, query),
    [filters, city, query],
  );
  // remember: «Назад» из объявления сразу показывает тот же список на той же прокрутке
  const { data, error, loading, reload } = useApi<ListingsPage>(
    `/api/listings?page=${page}&per_page=${isMap ? MAP_PER_PAGE : LISTINGS_PER_PAGE}${searchQuery ? `&${searchQuery}` : ''}`,
    { remember: true },
  );
  // Карта не пропадает, пока грузятся точки другой страницы или фильтра: старые точки
  // остаются, сверху «Обновляем…»
  const [shown, setShown] = useState(data);
  if (data && data !== shown) setShown(data);
  const mapData = data ?? (loading ? shown : undefined);
  const { groups, missing } = useMemo(() => groupByBuilding(mapData?.items ?? []), [mapData]);
  // Названия — всех районов (чипы, карточки); в фильтре и подсказках — только районы города
  const { names } = useDistricts();
  const districts = useCityDistricts(city);
  const filtered = hasFilters(filters);
  // Есть что сбрасывать: фильтры или текст поиска
  const narrowed = filtered || query !== '';

  const fallback = useMemo<MapFallback>(() => {
    const codes = cityCodes(city);
    const only = codes.length === 1 ? cities.cities.find((item) => item.code === codes[0]) : undefined;
    if (typeof only?.latitude === 'number' && typeof only.longitude === 'number') {
      return { latitude: only.latitude, longitude: only.longitude, zoom: CITY_ZOOM };
    }
    return GEORGIA;
  }, [city, cities.cities]);

  useDocumentTitle(`${ht.page_title} — bina.ai`);
  useTelegramBackButton(RENT_PATH);

  const search = (text: string) => {
    setQuery(text, smartPreferred && canSmartSearch(text));
    // На телефоне результаты ниже экрана — показываем их начало
    if (text && window.matchMedia('(pointer: coarse)').matches) {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Что нашлось: «Найдено 320 квартир по запросу «…»» или «… в районе Чугурети»
  const districtIds = filterDistricts(filters);
  const districtEntry = districtIds.length === 1 ? names[districtIds[0] ?? ''] : undefined;
  let summary = '';
  if (data && data.total > 0 && narrowed) {
    if (query) summary = fillVars(plural(ht.found_query, data.total, lang), { q: query });
    else if (districtEntry) {
      summary = fillVars(plural(ht.found_district, data.total, lang), {
        q: tr(districtEntry, lang),
      });
    } else summary = plural(ht.found, data.total, lang);
  }

  const toggleSmart = (next: boolean) => {
    saveSmartSearch(next);
    // Убираем и sort=smart из ссылки, и обычную сортировку: дальше решает запомненный выбор
    setSort(undefined);
  };

  useEffect(() => {
    if (!scrollToMap.current || !mapRef.current) return;
    scrollToMap.current = false;
    mapRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  const changeView = (next: typeof view) => {
    scrollToMap.current = next === 'map';
    setView(next);
  };

  const changePage = (next: number) => {
    if (isMap) {
      // Новые точки — на той же карте: прокручиваем к ней, а не наверх страницы
      scrollToMap.current = true;
      setPage(next, true);
      return;
    }
    setPage(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <section className="search-page space-y-6" aria-labelledby="search-title">
      <header className="search-page__header py-2 sm:py-4">
        <h1 id="search-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
          {ht.page_title}
        </h1>
      </header>

      <section className="search-page__filters flex flex-col gap-4" aria-label={ht.filters}>
        <div className="search-page__modes flex flex-wrap items-center gap-2">
          <CityPicker
            city={city}
            cities={cities.cities}
            loading={cities.loading}
            failed={cities.error !== undefined}
            onRetry={cities.reload}
            onChange={setCity}
          />
          <RentPeriodToggle
            value={isDaily(filters) ? 'daily' : 'monthly'}
            onChange={setRentPeriod}
          />
        </div>
        <SearchBar
          query={query}
          districts={districts}
          selectedDistricts={filterDistricts(filters)}
          onSearch={search}
          onSelectDistrict={addDistrict}
          loading={loading}
        >
          <FilterButton count={countFilters(filters)} onClick={openFilters} />
        </SearchBar>
        {smartAvailable && <SmartSearchToggle checked={smart} onChange={toggleSmart} />}
        <FilterChips
          filters={filters}
          districtNames={names}
          onRemove={setFilters}
          onEdit={openFilters}
        />
        <div className="search-page__filter-actions flex flex-wrap items-center gap-3">
          <SaveSearchButton filters={savedFilters} />
          {narrowed && (
            <button
              type="button"
              className="search-page__reset inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-md)] px-3 py-2.5 text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] active:scale-[.98]"
              onClick={() => {
                haptic('light');
                resetFilters();
              }}
            >
              <Icon name="close" className="size-4" />
              {ht.reset_filters}
            </button>
          )}
        </div>
        <FilterModal
          open={filtersOpen}
          onClose={closeFilters}
          filters={filters}
          city={city}
          query={query}
          smart={smart}
          districts={districts}
          onApply={replaceFilters}
        />
      </section>

      <section
        ref={resultsRef}
        className="search-page__listings scroll-mt-4 space-y-6"
        aria-labelledby="search-listings-title"
        aria-busy={loading}
      >
        <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 space-y-1">
            <h2
              id="search-listings-title"
              className="break-words text-xl font-bold tracking-tight"
              aria-live="polite"
            >
              {summary || (narrowed ? ht.results : ht.featured)}
            </h2>
            {data && !narrowed && (
              <p className="m-0 text-sm text-[var(--text-secondary)]">
                {fill(ht.count, data.total)}
              </p>
            )}
          </div>
          <div className="search-page__view flex flex-wrap items-center gap-2">
            <SearchViewToggle value={view} onChange={changeView} />
            {/* По смыслу порядок задаёт сервер — выбирать сортировку нечем */}
            {!smart && <SortSelect value={sort} byRelevance={query !== ''} onChange={setSort} />}
          </div>
        </header>

        {isMap && loading && !mapData && (
          <div ref={mapRef} className={MAP_BOX_CLASS}>
            <div className={MAP_SKELETON_CLASS} aria-hidden="true" />
          </div>
        )}

        {loading && !isMap && (
          <div className={GRID_CLASS}>
            {Array.from({ length: SKELETON_COUNT }, (_, index) => (
              <Skeleton key={index} />
            ))}
          </div>
        )}

        {error && <ErrorState onRetry={reload} />}

        {data && data.items.length === 0 && query && (
          <EmptyState
            icon="🔍"
            title={fill(ht.search_empty_title, query)}
            text={ht.search_empty_text}
          >
            {/* Убирает только текст поиска: фильтры остаются */}
            <button
              type="button"
              className={PRIMARY_BUTTON_CLASS}
              onClick={() => {
                haptic('light');
                setQuery('');
              }}
            >
              {ht.search_reset}
            </button>
          </EmptyState>
        )}

        {data && data.items.length === 0 && !query && (
          <EmptyState title={ht.empty_title} text={ht.empty_text}>
            {filtered && (
              <button
                type="button"
                className={PRIMARY_BUTTON_CLASS}
                onClick={() => {
                  haptic('light');
                  resetFilters();
                }}
              >
                {ht.reset_filters}
              </button>
            )}
          </EmptyState>
        )}

        {isMap && mapData && mapData.items.length > 0 && (
          <>
            <div ref={mapRef} className={MAP_BOX_CLASS}>
              <Suspense fallback={<div className={MAP_SKELETON_CLASS} aria-hidden="true" />}>
                <SearchMap groups={groups} fallback={fallback} districtNames={names} />
              </Suspense>
              {loading && (
                <p className="search-page__map-updating pointer-events-none absolute left-1/2 top-3 z-10 m-0 -translate-x-1/2 rounded-full bg-[var(--surface)] px-3 py-1.5 text-xs font-semibold text-[var(--text-secondary)] shadow-[var(--shadow-md)]">
                  {mt.updating}
                </p>
              )}
            </div>
            {missing > 0 && (
              <p className="search-page__map-missing m-0 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[var(--text-secondary)]">
                <span>{plural(mt.missing, missing, lang)}</span>
                <button
                  type="button"
                  className="inline-flex min-h-11 items-center font-semibold text-[var(--primary)] underline-offset-4 hover:underline"
                  onClick={() => {
                    haptic('light');
                    setView('list');
                  }}
                >
                  {mt.show_list}
                </button>
              </p>
            )}
            <Pagination current={mapData.page} total={mapData.pages} onChange={changePage} />
          </>
        )}

        {!isMap && data && data.items.length > 0 && (
          <>
            <div className={GRID_CLASS}>
              {data.items.map((listing) => (
                <ListingCard
                  key={listing.id}
                  listing={listing}
                  districtNames={names}
                  headingLevel="h3"
                  comparable
                />
              ))}
            </div>
            <Pagination current={data.page} total={data.pages} onChange={changePage} />
          </>
        )}
      </section>
      <CompareBar />
    </section>
  );
}
