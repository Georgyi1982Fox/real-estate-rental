import { useParams } from 'react-router-dom';
import type { AgencyPublic } from '../api/types';
import AgencyLogo from '../components/AgencyLogo';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import ListingCard from '../components/ListingCard';
import ShareButton from '../components/ShareButton';
import Skeleton from '../components/Skeleton';
import { useApi } from '../hooks/useApi';
import { useDistricts } from '../hooks/useDistricts';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { agencyShare } from '../lib/agency';
import { useI18n } from '../providers/I18nProvider';
import NotFoundPage from './NotFoundPage';

const SKELETON_COUNT = 3;
const GRID_CLASS = 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';

/** Страница агентства для всех (`/agency/:id`): открывается по ссылке без входа */
export default function AgencyPage() {
  const { id = '' } = useParams();
  const { t } = useI18n();
  const at = t.agency;
  const { names } = useDistricts();
  const { data, error, loading, reload } = useApi<AgencyPublic>(
    id ? `/api/agencies/${encodeURIComponent(id)}` : null,
  );

  useDocumentTitle(data ? `${data.name} — bina.ai` : 'bina.ai');
  useTelegramBackButton('/search');

  // 422 — в ссылке не ID агентства
  if (!id || error?.isNotFound || error?.status === 422) return <NotFoundPage />;

  return (
    <section className="agency-page flex flex-col gap-6" aria-labelledby="agency-page-title">
      {data && (
        <header className="agency-page__header flex flex-col gap-3 py-2 sm:py-4">
          <div className="flex min-w-0 items-center gap-4">
            <AgencyLogo
              url={data.logo_url}
              className="size-20 rounded-2xl"
              iconClassName="size-9 stroke-[1.5]"
            />
            <div className="min-w-0 flex-1 space-y-2">
              <h1
                id="agency-page-title"
                className="break-words text-2xl font-bold leading-tight tracking-tight sm:text-3xl"
              >
                {data.name}
              </h1>
              <ShareButton share={agencyShare(String(data.id), data.name)} label={at.share} />
            </div>
          </div>
          {data.description && (
            <p className="m-0 max-w-2xl whitespace-pre-line break-words text-sm leading-relaxed text-[var(--text-secondary)]">
              {data.description}
            </p>
          )}
        </header>
      )}

      {loading && (
        <div className={GRID_CLASS} aria-hidden="true">
          {Array.from({ length: SKELETON_COUNT }, (_, index) => (
            <Skeleton key={index} />
          ))}
        </div>
      )}

      {error && <ErrorState onRetry={reload} />}

      {data && data.listings.length === 0 && <EmptyState title={at.page_empty} />}

      {data && data.listings.length > 0 && (
        <ul className={`agency-page__list m-0 list-none p-0 ${GRID_CLASS}`}>
          {data.listings.map((listing) => (
            <li key={listing.id} className="min-w-0">
              <ListingCard listing={listing} districtNames={names} showAgency={false} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
