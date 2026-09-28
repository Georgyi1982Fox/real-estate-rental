import { Link } from 'react-router-dom';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import ListingCard from '../components/ListingCard';
import Skeleton from '../components/Skeleton';
import { useDistricts } from '../hooks/useDistricts';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useFavoriteListings } from '../hooks/useFavoriteListings';
import { useFavorites } from '../hooks/useFavorites';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { fill } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';

const MAX_SKELETONS = 4;
const GRID_CLASS = 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';

export default function FavoritesPage() {
  const { t } = useI18n();
  const ft = t.favorites;
  const { ids, remove } = useFavorites();
  const { names } = useDistricts();
  // Последние добавленные — сверху
  const newestFirst = [...ids].reverse();
  const { listings, error, loading, reload } = useFavoriteListings(newestFirst);

  useDocumentTitle(`${ft.page_title} — Bina.ai`);
  useTelegramBackButton('/');

  const isEmpty = ids.length === 0 || (!loading && !error && listings.length === 0);

  return (
    <section className="favorites space-y-6" aria-labelledby="favorites-title" aria-busy={loading}>
      <header className="favorites__header flex items-baseline justify-between gap-3 py-2 sm:py-4">
        <h1 id="favorites-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
          {ft.heading}
        </h1>
        {listings.length > 0 && (
          <span className="text-sm text-[var(--text-secondary)]">
            {fill(ft.count, listings.length)}
          </span>
        )}
      </header>

      {isEmpty && (
        <EmptyState icon="♡" title={ft.empty_title} text={ft.empty_text}>
          <Link
            to="/"
            className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]"
          >
            {ft.find}
          </Link>
        </EmptyState>
      )}

      {!isEmpty && loading && (
        <div className={GRID_CLASS}>
          {Array.from({ length: Math.min(ids.length, MAX_SKELETONS) }, (_, index) => (
            <Skeleton key={index} />
          ))}
        </div>
      )}

      {!isEmpty && error && <ErrorState onRetry={reload} />}

      {!isEmpty && listings.length > 0 && (
        <ul className={`favorites__list ${GRID_CLASS}`}>
          {listings.map((listing) => (
            <li key={listing.id} className="favorites__item flex min-w-0 flex-col gap-2">
              <ListingCard listing={listing} districtNames={names} />
              <button
                type="button"
                className="favorites__remove inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-2.5 text-sm font-semibold text-[var(--danger)] transition-colors duration-200 hover:bg-[var(--surface-hover)] active:scale-[.98]"
                onClick={() => remove(listing.id)}
              >
                <span aria-hidden="true">✕</span>
                <span>{ft.remove}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
