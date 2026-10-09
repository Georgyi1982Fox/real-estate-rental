import { useCallback, useMemo, useRef, useState } from 'react';
import type { ListingsPage } from '../api/types';
import CityPicker from '../components/CityPicker';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import FilterButton from '../components/FilterButton';
import FilterChips from '../components/FilterChips';
import FilterModal from '../components/FilterModal';
import Icon from '../components/Icon';
import ListingCard from '../components/ListingCard';
import Pagination from '../components/Pagination';
import RentPeriodToggle from '../components/RentPeriodToggle';
import SaveSearchButton from '../components/SaveSearchButton';
import SearchBar from '../components/SearchBar';
import Skeleton from '../components/Skeleton';
import SortSelect from '../components/SortSelect';
import { useApi } from '../hooks/useApi';
import { cityParam, useCity } from '../hooks/useCity';
import { useCityDistricts, useDistricts } from '../hooks/useDistricts';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useSearchFilters } from '../hooks/useSearchFilters';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { fill, fillVars, plural, tr } from '../lib/format';
import {
  countFilters,
  filterDistricts,
  hasFilters,
  isDaily,
  searchToQuery,
  withQuery,
} from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

const LISTINGS_PER_PAGE = 6;
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
  } = useSearchFilters();
  const [filtersOpen, setFiltersOpen] = useState(false);
  const openFilters = useCallback(() => setFiltersOpen(true), []);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeFilters = useCallback(() => setFiltersOpen(false), []);
  const resultsRef = useRef<HTMLElement>(null);
  const cities = useCity();
  // Город из ссылки (?city=…) важнее запомненного; undefined — «Вся Грузия»
  const city = urlCity === undefined ? cities.city : cityParam(urlCity);
  const searchQuery = searchToQuery({ ...filters, city }, query, sort);
  // Поиск сохраняется целиком: город + фильтры + текст из строки поиска (без сортировки).
  // Сайт не передаём: сохранённые поиски его ещё не хранят
  const savedFilters = useMemo(
    () => withQuery({ ...filters, source: undefined, city }, query),
    [filters, city, query],
  );
  // remember: «Назад» из объявления сразу показывает тот же список на той же прокрутке
  const { data, error, loading, reload } = useApi<ListingsPage>(
    `/api/listings?page=${page}&per_page=${LISTINGS_PER_PAGE}${searchQuery ? `&${searchQuery}` : ''}`,
    { remember: true },
  );
  // Названия — всех районов (чипы, карточки); в фильтре и подсказках — только районы города
  const { names } = useDistricts();
  const districts = useCityDistricts(city);
  const filtered = hasFilters(filters);
  // Есть что сбрасывать: фильтры или текст поиска
  const narrowed = filtered || query !== '';

  useDocumentTitle(`${ht.page_title} — bina.ai`);
  useTelegramBackButton('/');

  const search = (text: string) => {
    setQuery(text);
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

  const changePage = (next: number) => {
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
          <SortSelect value={sort} byRelevance={query !== ''} onChange={setSort} />
        </header>

        {loading && (
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

        {data && data.items.length > 0 && (
          <>
            <div className={GRID_CLASS}>
              {data.items.map((listing) => (
                <ListingCard
                  key={listing.id}
                  listing={listing}
                  districtNames={names}
                  headingLevel="h3"
                />
              ))}
            </div>
            <Pagination current={data.page} total={data.pages} onChange={changePage} />
          </>
        )}
      </section>
    </section>
  );
}
