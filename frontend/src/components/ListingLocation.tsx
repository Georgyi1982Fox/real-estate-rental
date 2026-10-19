import { Suspense, lazy, useCallback, useState } from 'react';
import type { Ref } from 'react';
import type { ListingLocation as LocationData } from '../api/types';
import { fill } from '../lib/format';
import { mapLinks } from '../lib/maps';
import type { MapTarget } from '../lib/maps';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import ExternalLink from './ExternalLink';
import Icon from './Icon';
import MapChooser from './MapChooser';

// Leaflet (~150 КБ) нужен только здесь — отдельный чанк
const ListingMap = lazy(() => import('./ListingMap'));

const MAP_BUTTON_CLASS =
  'listing-location__link inline-flex min-h-11 items-center justify-center gap-1.5 whitespace-nowrap rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-center text-sm font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-hover)] active:scale-[.98]';

interface ListingLocationProps {
  /** Ссылка «На карте» под заголовком объявления прокручивает к этому блоку */
  ref?: Ref<HTMLElement>;
  /** Ответ GET /api/listings/{id}/location; undefined — ещё грузится или ошибка */
  location: LocationData | undefined;
  loading: boolean;
  /** Адрес и район из самого объявления — пока /location не ответил */
  address: string;
  district: string;
  /** Подпись карты для скринридера; по умолчанию — «Квартира на карте» */
  mapLabel?: string;
}

/** Есть ли что показать на карте: точность exact/district и настоящие координаты */
export function hasMapPoint(
  location: LocationData | undefined,
): location is LocationData & { latitude: number; longitude: number } {
  if (!location || (location.precision !== 'exact' && location.precision !== 'district'))
    return false;
  return Number.isFinite(location.latitude) && Number.isFinite(location.longitude);
}

/** Что открыть во внешних картах: точку, если она известна, иначе — адрес текстом */
export function mapTarget(location: LocationData | undefined, place: string): MapTarget {
  return hasMapPoint(location)
    ? { latitude: location.latitude, longitude: location.longitude }
    : { query: place };
}

/**
 * «Расположение»: адрес, карта и кнопки внешних карт. Точка известна — метка,
 * известен только район — круг и подпись «Примерно: район …», иначе карты нет.
 * Нажатие на адрес — выбор: Google Maps или Яндекс Карты.
 */
export default function ListingLocation({
  ref,
  location,
  loading,
  address,
  district,
  mapLabel,
}: ListingLocationProps) {
  const { t } = useI18n();
  const lt = t.listing;
  const label = mapLabel ?? lt.map.label;
  const showMap = hasMapPoint(location);
  const districtName = location?.district || district;
  const place = address || location?.address || districtName;
  const [chooserOpen, setChooserOpen] = useState(false);
  const closeChooser = useCallback(() => setChooserOpen(false), []);
  const target = mapTarget(location, place);
  const links = mapLinks(target);
  // Ссылки бэкенда точнее (у него бывает адрес на языке карты); иначе — свои
  const google = location?.links?.google || links?.google || '';
  const yandex = location?.links?.yandex || links?.yandex || '';

  return (
    <section
      ref={ref}
      className="listing-location scroll-mt-24 space-y-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5"
      aria-labelledby="listing-location-title"
    >
      <h2 id="listing-location-title" className="text-lg font-semibold">
        {lt.location}
      </h2>
      {place && (
        <button
          type="button"
          className="listing-location__place group flex w-full items-start gap-2 rounded-[var(--radius-md)] text-left text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          aria-haspopup="dialog"
          onClick={() => {
            haptic('light');
            setChooserOpen(true);
          }}
        >
          <Icon name="pin" className="mt-0.5 size-4 shrink-0 text-[var(--primary)]" />
          <address className="min-w-0 flex-1 break-words not-italic underline decoration-dotted underline-offset-4">
            {place}
          </address>
          <span className="inline-flex shrink-0 items-center gap-1 text-xs font-semibold text-[var(--primary)]">
            <Icon name="map" className="size-4" />
            {lt.map.open}
          </span>
        </button>
      )}

      {loading && (
        <div
          className="listing-location__skeleton h-52 w-full animate-pulse rounded-[var(--radius-md)] bg-[var(--surface-hover)]"
          aria-hidden="true"
        />
      )}

      {showMap && (
        <figure className="listing-location__map space-y-2">
          {/* isolate: слои Leaflet (z-index до 1000) не вылезают поверх шапки и модалок */}
          <div className="listing-location__canvas isolate h-52 w-full overflow-hidden rounded-[var(--radius-md)] bg-[var(--surface-hover)]">
            <Suspense fallback={null}>
              <ListingMap
                latitude={location.latitude}
                longitude={location.longitude}
                exact={location.precision === 'exact'}
                label={label}
              />
            </Suspense>
          </div>
          {location.precision === 'district' && districtName && (
            <figcaption className="text-xs text-[var(--text-secondary)]">
              {fill(lt.map.approx, districtName)}
            </figcaption>
          )}
        </figure>
      )}

      {/* Обе карты — всегда, когда есть точка или хотя бы адрес */}
      {(google || yandex) && (
        <nav
          className={`listing-location__links grid gap-3 ${yandex ? 'grid-cols-2' : 'grid-cols-1'}`}
          aria-label={label}
        >
          {google && (
            <ExternalLink href={google} className={MAP_BUTTON_CLASS}>
              {lt.map.google}
              <Icon name="external" className="size-3.5" />
            </ExternalLink>
          )}
          {yandex && (
            <ExternalLink href={yandex} className={MAP_BUTTON_CLASS}>
              {lt.map.yandex}
              <Icon name="external" className="size-3.5" />
            </ExternalLink>
          )}
        </nav>
      )}

      <MapChooser open={chooserOpen} onClose={closeChooser} target={target} place={place} />
    </section>
  );
}
