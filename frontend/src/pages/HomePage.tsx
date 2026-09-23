import { useSearchParams } from 'react-router-dom';
import type { ListingsPage } from '../api/types';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import FilterPanel from '../components/FilterPanel';
import ListingCard from '../components/ListingCard';
import Pagination from '../components/Pagination';
import SearchBar from '../components/SearchBar';
import Skeleton from '../components/Skeleton';
import { useApi } from '../hooks/useApi';
import { useDistricts } from '../hooks/useDistricts';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { fill } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';

const LISTINGS_PER_PAGE = 6;
const SKELETON_COUNT = 4;
const GRID_CLASS = 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';

export default function HomePage() {
  const { t } = useI18n();
  const ht = t.home;
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number.parseInt(searchParams.get('page') ?? '1', 10) || 1);
  const { data, error, loading, reload } = useApi<ListingsPage>(
    `/api/listings?page=${page}&per_page=${LISTINGS_PER_PAGE}`,
  );
  const { districts, names } = useDistricts();

  useDocumentTitle(`Bina.ai — ${ht.page_title}`);

  const changePage = (next: number) => {
    setSearchParams((params) => {
      params.set('page', String(next));
      return params;
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <section className="home space-y-6" aria-labelledby="home-title">
      <header className="home__hero space-y-2 py-4 sm:py-8">
        <p className="text-sm font-medium text-[var(--primary)]">Bina.ai</p>
        <h1 id="home-title" className="max-w-2xl text-3xl font-bold tracking-tight sm:text-4xl">
          {ht.heading}
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-[var(--text-secondary)] sm:text-base">{ht.subtitle}</p>
      </header>

      <SearchBar />
      <FilterPanel districts={districts} />

      <section className="home__listings space-y-6" aria-labelledby="home-listings-title" aria-busy={loading}>
        <header className="flex items-baseline justify-between gap-3">
          <h2 id="home-listings-title" className="text-xl font-bold tracking-tight">
            {ht.featured}
          </h2>
          {data && <span className="text-sm text-[var(--text-secondary)]">{fill(ht.count, data.total)}</span>}
        </header>

        {loading && (
          <div className={GRID_CLASS}>
            {Array.from({ length: SKELETON_COUNT }, (_, index) => (
              <Skeleton key={index} />
            ))}
          </div>
        )}

        {error && <ErrorState onRetry={reload} />}

        {data && data.items.length === 0 && <EmptyState title={ht.empty_title} text={ht.empty_text} />}

        {data && data.items.length > 0 && (
          <>
            <div className={GRID_CLASS}>
              {data.items.map((listing) => (
                <ListingCard key={listing.id} listing={listing} districtNames={names} headingLevel="h3" />
              ))}
            </div>
            <Pagination current={data.page} total={data.pages} onChange={changePage} />
          </>
        )}
      </section>
    </section>
  );
}
