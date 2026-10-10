import { useCallback, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { Hotel, ListingLocation as LocationData } from '../api/types';
import ComplaintModal from '../components/ComplaintModal';
import ErrorState from '../components/ErrorState';
import Gallery from '../components/Gallery';
import HotelContacts from '../components/HotelContacts';
import HotelInfo from '../components/HotelInfo';
import HotelPrice from '../components/HotelPrice';
import HotelRooms from '../components/HotelRooms';
import Icon from '../components/Icon';
import ListingDescription from '../components/ListingDescription';
import ListingLocation from '../components/ListingLocation';
import ListingSkeleton from '../components/ListingSkeleton';
import PromotionBadges from '../components/PromotionBadges';
import RatingStars from '../components/RatingStars';
import { useApi } from '../hooks/useApi';
import { useCity } from '../hooks/useCity';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useGoBack, useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { hotelKindName } from '../i18n/hotels';
import { tr } from '../lib/format';
import { HOTELS_PATH } from '../lib/hotels';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import NotFoundPage from './NotFoundPage';

/** Страница гостиницы: галерея, сводка с контактами, удобства, описание, номера, карта */
export default function HotelPage() {
  const { id = '' } = useParams();
  // ID — строка как есть (UUID с бэкенда или число из моков)
  const hotelId = id ? encodeURIComponent(id) : null;
  const { lang, t } = useI18n();
  const ht = t.hotels;
  const { names: cityNames } = useCity();
  const {
    data: hotel,
    error,
    loading,
    reload,
  } = useApi<Hotel>(hotelId !== null ? `/api/hotels/${hotelId}` : null);
  const locationRef = useRef<HTMLElement>(null);
  const [complaintOpen, setComplaintOpen] = useState(false);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeComplaint = useCallback(() => setComplaintOpen(false), []);

  useTelegramBackButton(HOTELS_PATH);
  // Ссылка «← Назад» ведёт туда же, куда нативная кнопка Telegram: в тот же список
  const goBack = useGoBack(HOTELS_PATH);

  const name = hotel ? tr(hotel.name, lang) : '';
  useDocumentTitle(name ? `${name} — bina.ai` : 'bina.ai');

  const address = hotel?.address?.trim() ?? '';
  // Точку ставит сам хозяин — она всегда точная
  const location = useMemo<LocationData | undefined>(() => {
    const latitude = hotel?.latitude;
    const longitude = hotel?.longitude;
    if (typeof latitude !== 'number' || typeof longitude !== 'number') return undefined;
    return { precision: 'exact', latitude, longitude, district: null, address: address || null };
  }, [hotel, address]);

  if (hotelId === null || error?.isNotFound) return <NotFoundPage />;

  const kind = hotel ? hotelKindName(hotel.kind, lang) : undefined;
  const cityEntry = hotel ? cityNames[hotel.city] : undefined;
  const city = hotel ? (cityEntry ? tr(cityEntry, lang) : hotel.city) : '';
  const place = [address, city].filter(Boolean).join(', ');

  return (
    <>
      <nav className="hotel-page__breadcrumb mb-4" aria-label={ht.back}>
        <Link
          to={HOTELS_PATH}
          className="inline-flex items-center gap-1 rounded-[var(--radius-sm)] text-sm font-medium text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
          onClick={(event) => {
            // Новая вкладка (Ctrl/⌘ + щелчок) — обычная ссылка на список
            if (event.metaKey || event.ctrlKey || event.shiftKey) return;
            event.preventDefault();
            haptic('light');
            goBack();
          }}
        >
          <span aria-hidden="true">←</span> {ht.back}
        </Link>
      </nav>

      {loading && <ListingSkeleton />}
      {error && <ErrorState onRetry={reload} />}

      {hotel && (
        // key: при переходе на другую гостиницу состояние галереи и контактов сбрасывается
        <article
          key={hotel.id}
          className="hotel-page"
          data-hotel-id={hotel.id}
          aria-labelledby="hotel-title"
        >
          <div className="hotel-page__layout grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-8">
            <div className="hotel-page__media min-w-0 lg:col-start-1 lg:row-start-1">
              <Gallery images={hotel.images ?? []} alt={name} label={ht.gallery} />
            </div>

            {/* Сводка: на мобильном сразу под галереей, на десктопе — липкая правая колонка */}
            <section className="hotel-page__summary min-w-0 lg:col-start-2 lg:row-span-2 lg:row-start-1">
              <div className="hotel-summary space-y-5 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)] lg:sticky lg:top-6">
                <header className="hotel-summary__header space-y-2">
                  {(kind || typeof hotel.stars === 'number') && (
                    <p className="hotel-summary__kind m-0 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium text-[var(--text-secondary)]">
                      {kind && <span>{kind}</span>}
                      {typeof hotel.stars === 'number' && <RatingStars value={hotel.stars} />}
                    </p>
                  )}
                  <h1
                    id="hotel-title"
                    className="hotel-summary__title break-words text-2xl font-bold leading-tight tracking-tight"
                  >
                    {name}
                  </h1>
                  <PromotionBadges promoted={hotel.is_promoted} verified={hotel.is_verified} />
                  {place && (
                    <p className="hotel-summary__meta m-0 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[var(--text-secondary)]">
                      <span className="inline-flex min-w-0 items-start gap-1.5 break-words">
                        <Icon name="pin" className="mt-0.5 size-4" />
                        {place}
                      </span>
                      {location && (
                        <button
                          type="button"
                          className="hotel-summary__map rounded-[var(--radius-sm)] font-semibold text-[var(--text-primary)] underline underline-offset-2 transition-colors hover:text-[var(--text-secondary)]"
                          onClick={() => {
                            haptic('light');
                            locationRef.current?.scrollIntoView({
                              behavior: 'smooth',
                              block: 'start',
                            });
                          }}
                        >
                          {t.listing.on_map} ↓
                        </button>
                      )}
                    </p>
                  )}
                </header>

                <HotelPrice
                  price={hotel.min_price}
                  className="hotel-summary__price m-0 text-3xl font-bold tracking-tight"
                  periodClassName="text-base font-medium text-[var(--text-secondary)]"
                />

                <HotelContacts hotel={hotel} />

                <footer className="hotel-summary__footer">
                  <button
                    type="button"
                    className="hotel-summary__complain inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-md)] px-2 text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] active:scale-[.98]"
                    aria-haspopup="dialog"
                    onClick={() => {
                      haptic('light');
                      setComplaintOpen(true);
                    }}
                  >
                    <Icon name="flag" className="size-4" />
                    {t.complaint.button}
                  </button>
                </footer>
              </div>
            </section>

            <div className="hotel-page__details min-w-0 space-y-6 lg:col-start-1 lg:row-start-2">
              <HotelInfo hotel={hotel} />
              <ListingDescription text={tr(hotel.description, lang).trim()} />
              <HotelRooms rooms={hotel.rooms ?? []} />
              {location && (
                <ListingLocation
                  ref={locationRef}
                  location={location}
                  loading={false}
                  address={place}
                  district=""
                  mapLabel={ht.map_label}
                />
              )}
            </div>
          </div>

          <ComplaintModal
            open={complaintOpen}
            onClose={closeComplaint}
            path={`/api/hotels/${hotelId}/complaints`}
          />
        </article>
      )}
    </>
  );
}
