import { Suspense, lazy } from 'react';
import type { Ref } from 'react';
import type { ListingLocation as LocationData } from '../api/types';
import { fill } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import ExternalLink from './ExternalLink';

// Leaflet (~150 КБ) нужен только здесь — отдельный чанк
const ListingMap = lazy(() => import('./ListingMap'));

const MAP_BUTTON_CLASS =
  'listing-location__link inline-flex min-h-11 items-center justify-center gap-1 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-center text-sm font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-hover)] active:scale-[.98]';

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

/**
 * «Расположение»: адрес, карта и кнопки внешних карт. Точка известна — метка,
 * известен только район — круг и подпись «Примерно: район …», иначе карты нет.
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
  const google =
    location?.links?.google ||
    (showMap ? `https://www.google.com/maps?q=${location.latitude},${location.longitude}` : '');
  const yandex = location?.links?.yandex || '';

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
        <address className="break-words text-sm not-italic text-[var(--text-secondary)]">
          {place}
        </address>
      )}

      {loading && (
        <div
          className="listing-location__skeleton h-52 w-full animate-pulse rounded-[var(--radius-md)] bg-[var(--surface-hover)]"
          aria-hidden="true"
        />
      )}

      {showMap && (
        <>
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

          <nav
            className={`listing-location__links grid gap-3 ${yandex ? 'grid-cols-2' : 'grid-cols-1'}`}
            aria-label={label}
          >
            {google && (
              <ExternalLink href={google} className={MAP_BUTTON_CLASS}>
                {lt.map.google} ↗
              </ExternalLink>
            )}
            {yandex && (
              <ExternalLink href={yandex} className={MAP_BUTTON_CLASS}>
                {lt.map.yandex} ↗
              </ExternalLink>
            )}
          </nav>
        </>
      )}
    </section>
  );
}
