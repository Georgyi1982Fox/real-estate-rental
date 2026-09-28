import type { ListingsPage } from '../api/types';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import FilterPanel from '../components/FilterPanel';
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
import { filtersToQuery, hasFilters } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

const LISTINGS_PER_PAGE = 6;
const SKELETON_COUNT = 4;
const GRID_CLASS = 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';

export default function HomePage() {
  const { t } = useI18n();
  const ht = t.home;
  const { filters, page, setFilters, resetFilters, setPage } = useSearchFilters();
  const filterQuery = filtersToQuery(filters);
  const { data, error, loading, reload } = useApi<ListingsPage>(
    `/api/listings?page=${page}&per_page=${LISTINGS_PER_PAGE}${filterQuery ? `&${filterQuery}` : ''}`,
  );
  const { districts, names } = useDistricts();
  const filtered = hasFilters(filters);

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

      <SearchBar />

      <section className="home__filters flex flex-col gap-4" aria-label={ht.filters}>
        <FilterPanel districts={districts} filters={filters} onChange={setFilters} />
        <div className="home__filter-actions flex flex-wrap items-center gap-3">
          <SaveSearchButton filters={filters} />
          {filtered && (
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
      </section>

      <section
        className="home__listings space-y-6"
        aria-labelledby="home-listings-title"
        aria-busy={loading}
      >
        <header className="flex items-baseline justify-between gap-3">
          <h2 id="home-listings-title" className="text-xl font-bold tracking-tight">
            {filtered ? ht.results : ht.featured}
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

        {data && data.items.length === 0 && (
          <EmptyState title={ht.empty_title} text={ht.empty_text}>
            {filtered && (
              <button
                type="button"
                className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]"
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
