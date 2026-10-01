import { useCallback, useState } from 'react';
import type { ListingsPage } from '../api/types';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import FilterButton from '../components/FilterButton';
import FilterChips from '../components/FilterChips';
import FilterModal from '../components/FilterModal';
import Icon from '../components/Icon';
import ListingCard from '../components/ListingCard';
import Pagination from '../components/Pagination';
import SaveSearchButton from '../components/SaveSearchButton';
import SearchBar from '../components/SearchBar';
import Skeleton from '../components/Skeleton';
import { useApi } from '../hooks/useApi';
import { useDistricts } from '../hooks/useDistricts';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useSearchFilters } from '../hooks/useSearchFilters';
import { fill } from '../lib/format';
import { countFilters, filterDistricts, hasFilters, searchToQuery } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

const LISTINGS_PER_PAGE = 6;
const SKELETON_COUNT = 4;
const GRID_CLASS = 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';
const PRIMARY_BUTTON_CLASS =
  'inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]';

export default function HomePage() {
  const { t } = useI18n();
  const ht = t.home;
  const {
    filters,
    query,
    page,
    setFilters,
    replaceFilters,
    resetFilters,
    setQuery,
    addDistrict,
    setPage,
  } = useSearchFilters();
  const [filtersOpen, setFiltersOpen] = useState(false);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeFilters = useCallback(() => setFiltersOpen(false), []);
  const searchQuery = searchToQuery(filters, query);
  const { data, error, loading, reload } = useApi<ListingsPage>(
    `/api/listings?page=${page}&per_page=${LISTINGS_PER_PAGE}${searchQuery ? `&${searchQuery}` : ''}`,
  );
  const { districts, names } = useDistricts();
  const filtered = hasFilters(filters);
  // Есть что сбрасывать: фильтры или текст поиска
  const narrowed = filtered || query !== '';

  useDocumentTitle(`Bina.ai — ${ht.page_title}`);

  const changePage = (next: number) => {
    setPage(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <section className="home space-y-6" aria-labelledby="home-title">
      <header className="home__hero space-y-2 py-4 sm:py-8">
        <p className="text-sm font-medium text-[var(--primary)]">Bina.ai</p>
        <h1 id="home-title" className="max-w-2xl text-3xl font-bold tracking-tight sm:text-4xl">
          {ht.heading}
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-[var(--text-secondary)] sm:text-base">
          {ht.subtitle}
        </p>
      </header>

      <section className="home__filters flex flex-col gap-4" aria-label={ht.filters}>
        <SearchBar
          query={query}
          districts={districts}
          selectedDistricts={filterDistricts(filters)}
          onSearch={setQuery}
          onSelectDistrict={addDistrict}
        >
          <FilterButton count={countFilters(filters)} onClick={() => setFiltersOpen(true)} />
        </SearchBar>
        <FilterChips filters={filters} districtNames={names} onRemove={setFilters} />
        <div className="home__filter-actions flex flex-wrap items-center gap-3">
          <SaveSearchButton filters={filters} />
          {narrowed && (
            <button
              type="button"
              className="home__reset inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-md)] px-3 py-2.5 text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] active:scale-[.98]"
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
          query={query}
          districts={districts}
          onApply={replaceFilters}
        />
      </section>

      <section
        className="home__listings space-y-6"
        aria-labelledby="home-listings-title"
        aria-busy={loading}
      >
        <header className="flex items-baseline justify-between gap-3">
          <h2 id="home-listings-title" className="text-xl font-bold tracking-tight">
            {narrowed ? ht.results : ht.featured}
          </h2>
          {data && (
            <span className="text-sm text-[var(--text-secondary)]">
              {fill(ht.count, data.total)}
            </span>
          )}
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
