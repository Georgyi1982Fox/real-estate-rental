import { Link } from 'react-router-dom';
import type { Listing, ListingsPage } from '../api/types';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import ListingCard from '../components/ListingCard';
import Skeleton from '../components/Skeleton';
import { useApi } from '../hooks/useApi';
import { useDistricts } from '../hooks/useDistricts';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useFavorites } from '../hooks/useFavorites';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { fill } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';

// Временно: берём общий список и фильтруем по избранным ID.
// Со следующей задачей данные придут из GET /api/favorites.
const LISTINGS_PATH = '/api/listings?per_page=50';
const MAX_SKELETONS = 4;
const GRID_CLASS = 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';

export default function FavoritesPage() {
  const { t } = useI18n();
  const ft = t.favorites;
  const { ids, remove } = useFavorites();
  const { names } = useDistricts();
  // Пустое избранное — запрос не нужен
  const { data, error, loading, reload } = useApi<ListingsPage>(
    ids.length > 0 ? LISTINGS_PATH : null,
  );

  useDocumentTitle(`${ft.page_title} — Bina.ai`);
  useTelegramBackButton('/');

  // Порядок как в избранном, последние добавленные — сверху; ID сравниваем строками
  const byId = new Map<string, Listing>(
    data?.items.map((listing) => [String(listing.id), listing]),
  );
  const listings = [...ids]
    .reverse()
    .map((id) => byId.get(id))
    .filter((listing): listing is Listing => listing !== undefined);
  const isEmpty = ids.length === 0 || (data !== undefined && listings.length === 0);

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
