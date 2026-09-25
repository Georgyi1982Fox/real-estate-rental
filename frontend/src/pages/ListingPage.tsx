import { Link, useParams } from 'react-router-dom';
import type { ListResponse, Listing } from '../api/types';
import ContactButton from '../components/ContactButton';
import ErrorState from '../components/ErrorState';
import FavoriteButton from '../components/FavoriteButton';
import Gallery from '../components/Gallery';
import ListingDescription from '../components/ListingDescription';
import ListingSkeleton from '../components/ListingSkeleton';
import ListingSpecs from '../components/ListingSpecs';
import PhoneReveal from '../components/PhoneReveal';
import SimilarListings from '../components/SimilarListings';
import { useApi } from '../hooks/useApi';
import { useContact } from '../hooks/useContact';
import { useDistricts } from '../hooks/useDistricts';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { useTelegramMainButton } from '../hooks/useTelegramMainButton';
import { formatPrice, tr } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import NotFoundPage from './NotFoundPage';

export default function ListingPage() {
  const { id = '' } = useParams();
  const listingId = /^\d+$/.test(id) ? Number(id) : null;
  const { lang, t } = useI18n();
  const lt = t.listing;
  const { names } = useDistricts();
  const { data: listing, error, loading, reload } = useApi<Listing>(
    listingId !== null ? `/api/listings/${listingId}` : null,
  );
  const similar = useApi<ListResponse<Listing>>(
    listingId !== null ? `/api/listings/${listingId}/similar` : null,
  );

  useTelegramBackButton('/');

  // «Написать»: в Telegram — нативная MainButton внизу экрана, в браузере — обычная кнопка
  const { contact, loading: contactLoading } = useContact(listing?.id ?? null);
  const nativeContact = useTelegramMainButton({
    text: lt.write,
    onClick: contact,
    visible: Boolean(listing),
    loading: contactLoading,
  });

  const title = listing ? tr(listing.title, lang) : '';
  useDocumentTitle(title ? `${title} — Bina.ai` : 'Bina.ai');

  if (listingId === null || error?.isNotFound) return <NotFoundPage />;

  const districtEntry = listing ? names[listing.district] : undefined;
  const district = listing ? (districtEntry ? tr(districtEntry, lang) : listing.district) : '';
  const ownerName = tr(listing?.owner?.name, lang);
  const address = tr(listing?.address, lang);

  return (
    <>
      <nav className="listing-page__breadcrumb mb-4" aria-label={lt.back}>
        <Link
          to="/"
          className="inline-flex items-center gap-1 rounded-[var(--radius-sm)] text-sm font-medium text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
        >
          <span aria-hidden="true">←</span> {lt.back}
        </Link>
      </nav>

      {loading && <ListingSkeleton />}
      {error && <ErrorState onRetry={reload} />}

      {listing && (
        // key: при переходе на похожую квартиру состояние галереи/телефона/описания сбрасывается
        <article
          key={listing.id}
          className="listing-page"
          data-listing-id={listing.id}
          aria-labelledby="listing-title"
        >
          <div className="listing-page__layout grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-8">
            <div className="listing-page__media min-w-0 lg:col-start-1 lg:row-start-1">
              <Gallery images={listing.images ?? []} alt={title} />
            </div>

            {/* Сводка: на мобильном сразу под галереей, на десктопе — липкая правая колонка */}
            <section className="listing-page__summary min-w-0 lg:col-start-2 lg:row-span-2 lg:row-start-1">
              <div className="listing-summary space-y-5 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)] lg:sticky lg:top-6">
                <header className="listing-summary__header space-y-2">
                  <h1
                    id="listing-title"
                    className="listing-summary__title break-words text-2xl font-bold leading-tight tracking-tight"
                  >
                    {title}
                  </h1>
                  <p className="listing-summary__meta flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[var(--text-secondary)]">
                    <span className="inline-flex items-center gap-1">
                      <span aria-hidden="true">📍</span>
                      {district}
                    </span>
                    {typeof listing.rating === 'number' && (
                      <span className="inline-flex items-center gap-1">
                        <span className="text-[var(--accent)]" aria-hidden="true">
                          ★
                        </span>
                        <span className="sr-only">{lt.rating}:</span>
                        <span className="font-medium text-[var(--text-primary)]">{listing.rating.toFixed(1)}</span>
                      </span>
                    )}
                  </p>
                </header>

                <p className="listing-summary__price text-3xl font-bold tracking-tight">
                  {formatPrice(listing.price, listing.currency)}{' '}
                  <span className="text-base font-medium text-[var(--text-secondary)]">{lt.per_month}</span>
                </p>

                {ownerName && (
                  <p className="listing-summary__owner text-sm text-[var(--text-secondary)]">
                    {lt.owner}: <span className="font-medium text-[var(--text-primary)]">{ownerName}</span>
                  </p>
                )}

                <section
                  className={`listing-contact grid grid-cols-1 gap-3 lg:grid-cols-1 ${nativeContact ? 'sm:grid-cols-2' : 'sm:grid-cols-3'}`}
                  aria-label={lt.contact}
                >
                  {!nativeContact && <ContactButton onClick={contact} loading={contactLoading} />}
                  <PhoneReveal listingId={listing.id} />
                  <FavoriteButton />
                </section>
              </div>
            </section>

            <div className="listing-page__details min-w-0 space-y-6 lg:col-start-1 lg:row-start-2">
              <ListingSpecs listing={listing} />
              <ListingDescription text={tr(listing.description, lang).trim()} />

              <section
                className="listing-location space-y-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5"
                aria-labelledby="listing-location-title"
              >
                <h2 id="listing-location-title" className="text-lg font-semibold">
                  {lt.location}
                </h2>
                <address className="text-sm not-italic text-[var(--text-secondary)]">{address || district}</address>
                {/* Заглушка карты: будет заменена на реальную карту */}
                <figure className="listing-location__map grid aspect-[16/9] w-full place-items-center rounded-[var(--radius-md)] bg-[var(--surface-hover)]">
                  <figcaption className="flex flex-col items-center gap-2 text-sm text-[var(--text-secondary)]">
                    <span className="text-3xl" aria-hidden="true">
                      📍
                    </span>
                    {lt.map_soon}
                  </figcaption>
                </figure>
              </section>
            </div>
          </div>
        </article>
      )}

      {listing && (
        <SimilarListings
          listings={similar.data?.items}
          loading={similar.loading}
          failed={Boolean(similar.error)}
          onRetry={similar.reload}
          districtNames={names}
        />
      )}
    </>
  );
}
