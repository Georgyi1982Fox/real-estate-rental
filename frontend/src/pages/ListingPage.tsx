import { Link, useParams } from 'react-router-dom';
import type { ListResponse, Listing } from '../api/types';
import BookViewingButton from '../components/BookViewingButton';
import ContactButton from '../components/ContactButton';
import ErrorState from '../components/ErrorState';
import ExternalLink from '../components/ExternalLink';
import FavoriteButton from '../components/FavoriteButton';
import FraudWarning from '../components/FraudWarning';
import Gallery from '../components/Gallery';
import ListingDates from '../components/ListingDates';
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
import { fill, formatPrice, tr } from '../lib/format';
import { fraudLevel } from '../lib/fraud';
import { useI18n } from '../providers/I18nProvider';
import NotFoundPage from './NotFoundPage';

export default function ListingPage() {
  const { id = '' } = useParams();
  // ID — строка как есть (UUID с бэкенда или число из моков), в число не приводим
  const listingId = id ? encodeURIComponent(id) : null;
  const { lang, t } = useI18n();
  const lt = t.listing;
  const { names } = useDistricts();
  const {
    data: listing,
    error,
    loading,
    reload,
  } = useApi<Listing>(listingId !== null ? `/api/listings/${listingId}` : null);
  const similar = useApi<ListResponse<Listing>>(
    listingId !== null ? `/api/listings/${listingId}/similar` : null,
  );

  useTelegramBackButton('/search');

  // Хозяин разместил объявление сам: source_url — переписка с ним в боте (с AI-переводом),
  // а не сайт-источник
  const byOwner = listing?.source === 'owner';
  const writeLabel = byOwner ? lt.write_owner : lt.write;
  const chatUrl = byOwner ? (listing?.source_url ?? '') : '';

  // «Написать»: в Telegram — нативная MainButton внизу экрана, в браузере — обычная кнопка
  const { contact, loading: contactLoading } = useContact(listing?.id ?? null, listing?.source_url);
  const nativeContact = useTelegramMainButton({
    text: writeLabel,
    onClick: contact,
    visible: Boolean(listing),
    loading: contactLoading,
  });

  const title = listing ? tr(listing.title, lang) : '';
  // Сайт-источник для ссылки «Открыть на …»: myhome.ge, home.ss.ge → ss.ge
  const sourceSite = listing?.source_url && !byOwner ? siteName(listing.source_url) : '';
  // Кнопки связи: «Написать» (в браузере), «На просмотр», телефон, избранное.
  // Три — в один ряд на планшете, иначе по две
  const contactButtons = [!nativeContact, Boolean(chatUrl), listing?.has_phone, true].filter(
    Boolean,
  ).length;
  useDocumentTitle(title ? `${title} — Bina.ai` : 'Bina.ai');

  if (listingId === null || error?.isNotFound) return <NotFoundPage />;

  const districtEntry = listing ? names[listing.district] : undefined;
  const district = listing ? (districtEntry ? tr(districtEntry, lang) : listing.district) : '';
  const ownerName = tr(listing?.owner?.name, lang) || listing?.owner_name || '';
  const address = tr(listing?.address, lang);
  const mapUrl = listing ? googleMapsUrl(listing.latitude, listing.longitude) : '';

  return (
    <>
      <nav className="listing-page__breadcrumb mb-4" aria-label={lt.back}>
        <Link
          to="/search"
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
                    <span className="inline-flex min-w-0 items-start gap-1 break-words">
                      <span aria-hidden="true">📍</span>
                      {address ? `${address}, ${district}` : district}
                    </span>
                    {mapUrl && (
                      <ExternalLink
                        href={mapUrl}
                        className="listing-summary__map rounded-[var(--radius-sm)] font-semibold text-[var(--text-primary)] underline underline-offset-2 transition-colors hover:text-[var(--primary)]"
                      >
                        {lt.on_map} ↗
                      </ExternalLink>
                    )}
                    {typeof listing.rating === 'number' && (
                      <span className="inline-flex items-center gap-1">
                        <span className="text-[var(--accent)]" aria-hidden="true">
                          ★
                        </span>
                        <span className="sr-only">{lt.rating}:</span>
                        <span className="font-medium text-[var(--text-primary)]">
                          {listing.rating.toFixed(1)}
                        </span>
                      </span>
                    )}
                  </p>
                </header>

                <p className="listing-summary__price text-3xl font-bold tracking-tight">
                  {formatPrice(listing.price, listing.currency)}{' '}
                  <span className="text-base font-medium text-[var(--text-secondary)]">
                    {lt.per_month}
                  </span>
                </p>

                {ownerName && (
                  <p className="listing-summary__owner text-sm text-[var(--text-secondary)]">
                    {lt.owner}:{' '}
                    <span className="font-medium text-[var(--text-primary)]">{ownerName}</span>
                  </p>
                )}

                <FraudWarning level={fraudLevel(listing)} reasons={listing.fraud_reasons ?? []} />

                <section
                  className={`listing-contact grid grid-cols-1 gap-3 lg:grid-cols-1 ${contactButtons === 3 ? 'sm:grid-cols-3' : 'sm:grid-cols-2'}`}
                  aria-label={lt.contact}
                >
                  {!nativeContact && (
                    <ContactButton label={writeLabel} onClick={contact} loading={contactLoading} />
                  )}
                  {chatUrl && <BookViewingButton href={chatUrl} />}
                  {/* Кнопка телефона — только если он есть: иначе «Написать» ведёт на сайт-источник */}
                  {listing.has_phone && <PhoneReveal listingId={listing.id} />}
                  <FavoriteButton listingId={listing.id} />
                </section>

                {chatUrl && (
                  <p className="listing-contact__hint m-0 text-xs text-[var(--text-secondary)]">
                    {lt.translate_hint}
                  </p>
                )}

                {listing.source_url && sourceSite && (
                  <p className="listing-source m-0 text-sm text-[var(--text-secondary)]">
                    <ExternalLink
                      href={listing.source_url}
                      className="listing-source__link font-semibold text-[var(--primary)] underline-offset-2 hover:underline"
                    >
                      {fill(lt.open_source, sourceSite)} ↗
                    </ExternalLink>
                    {!listing.has_phone && <span className="block">{lt.source_hint}</span>}
                  </p>
                )}
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
                <address className="text-sm not-italic text-[var(--text-secondary)]">
                  {address || district}
                </address>
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

              <ListingDates publishedAt={listing.published_at} updatedAt={listing.updated_at} />
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

/** Ссылка «На карте»; координат нет (null, не число) — '' */
function googleMapsUrl(latitude?: number | null, longitude?: number | null): string {
  if (typeof latitude !== 'number' || typeof longitude !== 'number') return '';
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return '';
  return `https://www.google.com/maps?q=${latitude},${longitude}`;
}

/** Короткое имя сайта для подписи: www.myhome.ge → MyHome.ge, home.ss.ge → SS.ge */
function siteName(url: string): string {
  try {
    const host = new URL(url).hostname.replace(/^(www|home)\./, '');
    if (host === 'myhome.ge') return 'MyHome.ge';
    if (host === 'ss.ge') return 'SS.ge';
    return host;
  } catch {
    return '';
  }
}
