import { Link } from 'react-router-dom';
import type { DistrictInfo, DistrictTypicalPrice } from '../api/types';
import { useApi } from '../hooks/useApi';
import { fill, fillVars, formatPrice, plural } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

interface DistrictAboutProps {
  /** ID района объявления */
  districtId: string;
}

const CHIP_CLASS =
  'district-about__chip rounded-full bg-[var(--surface-hover)] px-2.5 py-1 text-xs font-medium leading-5';

/** Обычные цены по комнатам: бэкенд может прислать список или словарь { "1": 1100 } */
function typicalPrices(value: DistrictInfo['typical_prices']): DistrictTypicalPrice[] {
  const list = Array.isArray(value)
    ? value
    : Object.entries(value ?? {}).map(([rooms, price]) => ({ rooms: Number(rooms), price }));
  return list
    .filter((item) => Number.isFinite(item.rooms) && Number.isFinite(item.price) && item.price > 0)
    .sort((a, b) => a.rooms - b.rooms);
}

/**
 * «О районе»: время до центра, метро, метки, описание, число объявлений и обычные цены.
 * Справка доступна и без входа; пока грузится — скелетон, не пришла — блока нет.
 */
export default function DistrictAbout({ districtId }: DistrictAboutProps) {
  const { lang, t } = useI18n();
  const dt = t.listing.district;
  const { data, loading } = useApi<DistrictInfo>(
    districtId ? `/api/districts/${encodeURIComponent(districtId)}?lang=${lang}` : null,
  );

  if (loading) {
    return (
      <div
        className="district-about district-about--loading h-40 animate-pulse rounded-[var(--radius-lg)] bg-[var(--surface-hover)]"
        aria-hidden="true"
      />
    );
  }
  if (!data) return null;

  const currency = data.currency || 'GEL';
  const prices = typicalPrices(data.typical_prices);
  const chips = [
    typeof data.minutes_to_center === 'number' ? fill(dt.to_center, data.minutes_to_center) : '',
    typeof data.has_metro === 'boolean' ? (data.has_metro ? dt.metro_yes : dt.metro_no) : '',
    ...(data.tags ?? []),
  ].filter(Boolean);

  return (
    <section
      className="district-about space-y-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5"
      aria-labelledby="district-about-title"
    >
      <header className="district-about__header space-y-1">
        <h2 id="district-about-title" className="text-lg font-semibold">
          {dt.title}
        </h2>
        {data.name && <p className="break-words text-base font-semibold">{data.name}</p>}
      </header>

      {chips.length > 0 && (
        <ul className="district-about__chips flex list-none flex-wrap gap-2 p-0">
          {chips.map((chip, index) => (
            <li key={`${index}-${chip}`} className={CHIP_CLASS}>
              {chip}
            </li>
          ))}
        </ul>
      )}

      {data.description && (
        <p className="district-about__description whitespace-pre-line break-words text-sm leading-6 text-[var(--text-secondary)]">
          {data.description}
        </p>
      )}

      {typeof data.listings_count === 'number' && (
        <p className="district-about__count text-sm font-medium">
          {plural(dt.count, data.listings_count, lang)}
        </p>
      )}

      {prices.length > 0 && (
        <p className="district-about__prices break-words text-sm">
          <span className="text-[var(--text-secondary)]">{dt.typical}</span>{' '}
          {prices
            .map((item) =>
              fillVars(dt.typical_item, {
                rooms: item.rooms,
                price: formatPrice(item.price, currency),
              }),
            )
            .join(', ')}
        </p>
      )}

      {data.note && (
        <p className="district-about__note break-words text-xs text-[var(--text-secondary)]">
          {data.note}
        </p>
      )}

      <Link
        to={`/search?district=${encodeURIComponent(districtId)}`}
        onClick={() => haptic('light')}
        className="district-about__all inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-2.5 text-center text-sm font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-hover)] active:scale-[.98]"
      >
        {dt.all}
      </Link>
    </section>
  );
}
