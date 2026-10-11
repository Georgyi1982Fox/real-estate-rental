import type { Listing } from '../api/types';
import type { DistrictNames } from '../hooks/useDistricts';
import { useI18n } from '../providers/I18nProvider';
import ErrorState from './ErrorState';
import ListingCard from './ListingCard';
import Skeleton from './Skeleton';

interface AssistantCheaperProps {
  /** undefined — ещё не загружены */
  listings: Listing[] | undefined;
  loading: boolean;
  failed: boolean;
  onRetry: () => void;
  districtNames: DistrictNames;
}

const SKELETON_COUNT = 2;
// Как в «Похожих»: на телефоне — лента со свайпом (края блока — отступ p-5), от 640px — сетка
const TRACK_CLASS =
  'assistant-cheaper__track no-scrollbar -mx-5 my-0 flex list-none snap-x snap-mandatory scroll-px-5 gap-4 overflow-x-auto px-5 pb-2 pt-1 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-x-visible sm:px-0';
const ITEM_CLASS =
  'assistant-cheaper__item w-[80%] max-w-xs shrink-0 snap-start sm:w-auto sm:max-w-none';

/** «Похожие дешевле»: тот же район и комнаты, площадь ±20% — подбирает бэкенд, без AI */
export default function AssistantCheaper({
  listings,
  loading,
  failed,
  onRetry,
  districtNames,
}: AssistantCheaperProps) {
  const { t } = useI18n();
  const at = t.listing.assistant;

  return (
    <section className="assistant-cheaper" aria-label={at.cheaper} aria-busy={loading}>
      {loading && (
        <ul className={TRACK_CLASS}>
          {Array.from({ length: SKELETON_COUNT }, (_, index) => (
            <li key={index} className={ITEM_CLASS}>
              <Skeleton />
            </li>
          ))}
        </ul>
      )}

      {failed && <ErrorState compact onRetry={onRetry} />}

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
        <p className="assistant-cheaper__empty m-0 rounded-[var(--radius-md)] border border-dashed border-[var(--border)] px-4 py-8 text-center text-sm text-[var(--text-secondary)]">
          {at.cheaper_empty}
        </p>
      )}
    </section>
  );
}
