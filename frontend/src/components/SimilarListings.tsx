import type { Listing } from '../api/types';
import type { DistrictNames } from '../hooks/useDistricts';
import { useI18n } from '../providers/I18nProvider';
import ListingCard from './ListingCard';
import Skeleton from './Skeleton';

interface SimilarListingsProps {
  listings: Listing[] | undefined;
  loading: boolean;
  failed: boolean;
  onRetry: () => void;
  districtNames: DistrictNames;
}

const SKELETON_COUNT = 3;
// Мобильный: горизонтальная лента со свайпом; от 640px — обычная сетка
const TRACK_CLASS =
  'listing-similar__track no-scrollbar -mx-4 flex list-none snap-x snap-mandatory scroll-px-4 gap-4 overflow-x-auto px-4 pb-2 pt-1 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-x-visible sm:px-0 lg:grid-cols-3';
const ITEM_CLASS = 'listing-similar__item w-[80%] max-w-xs shrink-0 snap-start sm:w-auto sm:max-w-none';

export default function SimilarListings({ listings, loading, failed, onRetry, districtNames }: SimilarListingsProps) {
  const { t } = useI18n();
  const lt = t.listing;

  return (
    <section className="listing-similar mt-10 space-y-4" aria-labelledby="listing-similar-title" aria-busy={loading}>
      <h2 id="listing-similar-title" className="text-xl font-bold tracking-tight">
        {lt.similar}
      </h2>

      {loading && (
        <ul className={TRACK_CLASS}>
          {Array.from({ length: SKELETON_COUNT }, (_, index) => (
            <li key={index} className={ITEM_CLASS}>
              <Skeleton />
            </li>
          ))}
        </ul>
      )}

      {failed && (
        <p className="flex flex-wrap items-center justify-center gap-3 rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] py-10 text-center text-sm text-[var(--text-secondary)]" role="alert">
          {t.common.error_title}
          <button type="button" className="font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)]" onClick={onRetry}>
            ↻ {t.common.retry}
          </button>
        </p>
      )}

      {listings && listings.length > 0 && (
        <ul className={TRACK_CLASS}>
          {listings.map((listing) => (
            <li key={listing.id} className={ITEM_CLASS}>
              <ListingCard listing={listing} districtNames={districtNames} headingLevel="h3" />
            </li>
          ))}
        </ul>
      )}

      {listings && listings.length === 0 && (
        <p className="rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] py-10 text-center text-sm text-[var(--text-secondary)]">
          {lt.similar_empty}
        </p>
      )}
    </section>
  );
}
