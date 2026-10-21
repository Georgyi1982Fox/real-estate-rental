import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { ComparedListing, ListingComparison, ListingId } from '../api/types';
import { useDistricts } from '../hooks/useDistricts';
import { FEATURE_CODES, featureName } from '../i18n/features';
import type { Strings } from '../i18n/strings';
import { isBest } from '../lib/compare';
import { fill, formatDecimal, formatPrice, tr } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import ListingPrice from './ListingPrice';
import PriceLevelBadge, { isPriceLevel } from './PriceLevelBadge';

type RowCode = keyof Strings['compare']['rows'];

interface CompareTableProps {
  data: ListingComparison;
  /** ✕ в колонке квартиры */
  onRemove: (id: ListingId) => void;
}

const LABEL_CLASS =
  'compare-table__label w-28 min-w-28 border-b border-r border-[var(--border)] bg-[var(--surface)] p-3 text-left align-top text-xs font-medium leading-5 text-[var(--text-secondary)] sm:w-44 sm:min-w-44 sm:text-sm';
const CELL_CLASS =
  'compare-table__cell min-w-36 border-b border-[var(--border)] p-3 align-top leading-5 sm:min-w-48';
const BEST_CLASS =
  'compare-table__cell--best bg-[var(--success-bg)] text-[var(--success-text)] shadow-[inset_3px_0_0_var(--primary)]';
const MUTED = <span className="text-[var(--text-secondary)]">—</span>;

/** Подписи строк — свои по коду (весь экран на языке интерфейса); незнакомый код — с бэкенда */
function isKnownRow(code: string, rows: Strings['compare']['rows']): code is RowCode {
  return Object.hasOwn(rows, code);
}

/** Риск — тем же жёлтым значком ⚠️, что и на карточке; без признаков — зелёная галочка */
function RiskValue({ level }: { level: string }) {
  const { t } = useI18n();

  if (level !== 'warning' && level !== 'high') {
    return (
      <span className="inline-flex items-center gap-1.5 font-medium">
        <Icon name="check" className="size-4" />
        {t.compare.no_signs}
      </span>
    );
  }
  return (
    <span className="inline-flex items-start gap-2">
      <span className="inline-flex size-7 shrink-0 items-center justify-center rounded-full border border-white/60 bg-[var(--accent)] text-[var(--warning-ink)] shadow-[var(--shadow-sm)]">
        <Icon name="alert" className="size-4" />
      </span>
      <span className={level === 'high' ? 'font-semibold text-[var(--danger)]' : 'font-medium'}>
        {level === 'high' ? t.listing.fraud.high : t.listing.fraud.warning}
      </span>
    </span>
  );
}

/**
 * Таблица сравнения 2-3 квартир: колонки — квартиры, строки — из rows в их порядке.
 * Лучшее значение в строке (best) — зелёным; удобства — галочками по каждому удобству.
 * На узком экране колонки прокручиваются, подписи слева закреплены
 */
export default function CompareTable({ data, onRemove }: CompareTableProps) {
  const { lang, t } = useI18n();
  const ct = t.compare;
  const { items, best, currency } = data;
  // Район — на языке интерфейса, как в карточках; сервер присылает его на языке профиля
  const { names: districtNames } = useDistricts();

  const value = (code: string, item: ComparedListing): ReactNode => {
    switch (code) {
      case 'price':
        return formatPrice(item.price, currency);
      case 'price_per_m2':
        return typeof item.price_per_m2 === 'number'
          ? formatDecimal(item.price_per_m2, currency)
          : MUTED;
      case 'area':
        return `${item.area} ${t.card.sqm}`;
      case 'rooms':
        return String(item.rooms);
      case 'floor':
        if (typeof item.floor !== 'number') return MUTED;
        return typeof item.total_floors === 'number'
          ? `${item.floor}/${item.total_floors}`
          : String(item.floor);
      case 'district': {
        const names = districtNames[item.listing.district];
        return (names ? tr(names, lang) : item.district) || MUTED;
      }
      case 'minutes_to_center':
        return typeof item.minutes_to_center === 'number'
          ? fill(ct.minutes, item.minutes_to_center)
          : MUTED;
      case 'metro':
        if (typeof item.metro !== 'boolean') return MUTED;
        return item.metro ? ct.yes : ct.no;
      case 'move_in':
        return formatPrice(item.move_in, currency);
      case 'average_month':
        return formatPrice(item.average_month, currency);
      case 'price_level':
        return isPriceLevel(item.price_level) ? (
          <PriceLevelBadge level={item.price_level} className="text-xs sm:text-sm" />
        ) : (
          <span className="text-[var(--text-secondary)]">{ct.no_estimate}</span>
        );
      case 'risk_level':
        return <RiskValue level={item.risk_level} />;
      case 'features':
        return String(new Set(item.features).size);
      default: {
        // Новая строка с бэкенда: показываем простое значение как есть
        const raw: unknown = (item as unknown as Record<string, unknown>)[code];
        if (typeof raw === 'boolean') return raw ? ct.yes : ct.no;
        if (typeof raw === 'number' || (typeof raw === 'string' && raw !== '')) return String(raw);
        return MUTED;
      }
    }
  };

  const cell = (code: string, item: ComparedListing, content: ReactNode, emphasise = true) => {
    const top = isBest(best, code, item.listing.id);
    const tone = top ? BEST_CLASS : emphasise ? 'text-[var(--text-primary)]' : '';
    return (
      <td
        key={item.listing.id}
        className={`${CELL_CLASS} ${tone} ${emphasise || top ? 'font-semibold' : ''}`}
      >
        {content}
        {top && <span className="sr-only"> ({ct.best})</span>}
      </td>
    );
  };

  // Удобства — объединение по всем квартирам, в порядке словаря; незнакомые коды пропускаем
  const allFeatures = new Set(items.flatMap((item) => item.features));
  const features = FEATURE_CODES.filter((code) => allFeatures.has(code)).flatMap((code) => {
    const name = featureName(code, lang);
    return name ? [{ code, name }] : [];
  });

  return (
    <div
      className="compare-table relative overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)]"
      role="region"
      aria-label={ct.title}
      tabIndex={0}
    >
      <table className="compare-table__table w-full border-separate border-spacing-0 text-sm">
        <thead>
          <tr>
            <td className={`${LABEL_CLASS} align-bottom`} />
            {items.map((item) => {
              const { listing } = item;
              const title = tr(listing.title, lang);
              const image = listing.images?.[0];
              const to = `/listing/${encodeURIComponent(listing.id)}`;
              return (
                <th
                  key={listing.id}
                  scope="col"
                  className="compare-table__listing min-w-36 border-b border-[var(--border)] p-3 text-left align-top font-normal sm:min-w-48"
                >
                  <div className="relative">
                    <Link
                      to={to}
                      className="block overflow-hidden rounded-[var(--radius-md)] bg-[var(--surface-hover)]"
                      tabIndex={-1}
                      aria-hidden="true"
                      onClick={() => haptic('light')}
                    >
                      {image ? (
                        <img
                          className="aspect-[4/3] w-full object-cover"
                          src={image}
                          alt=""
                          loading="lazy"
                          width={192}
                          height={144}
                        />
                      ) : (
                        <span className="flex aspect-[4/3] w-full items-center justify-center p-2 text-center text-xs text-[var(--text-secondary)]">
                          {t.card.no_photo}
                        </span>
                      )}
                    </Link>
                    <button
                      type="button"
                      className="compare-table__remove absolute right-1.5 top-1.5 inline-flex size-9 items-center justify-center rounded-full border border-white/60 bg-white/90 text-[#0f172a] shadow-sm backdrop-blur-sm transition-colors hover:bg-white active:scale-[.95]"
                      aria-label={fill(ct.remove, title)}
                      title={fill(ct.remove, title)}
                      onClick={() => onRemove(listing.id)}
                    >
                      <Icon name="close" className="size-4" />
                    </button>
                  </div>
                  <Link
                    to={to}
                    className="mt-2 line-clamp-2 break-words text-sm font-semibold leading-5 text-[var(--text-primary)] underline-offset-2 hover:underline"
                    onClick={() => haptic('light')}
                  >
                    {title}
                  </Link>
                  <ListingPrice
                    listing={listing}
                    className="m-0 mt-1 text-sm text-[var(--text-secondary)]"
                    periodClassName="text-xs"
                  />
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => {
            const label = isKnownRow(row.code, ct.rows) ? ct.rows[row.code] : row.title;
            const badge = row.code === 'price_level' || row.code === 'risk_level';
            return [
              <tr key={row.code} className="compare-table__row">
                <th scope="row" className={LABEL_CLASS}>
                  {label}
                </th>
                {items.map((item) => cell(row.code, item, value(row.code, item), !badge))}
              </tr>,
              // Под строкой «Удобства» (их число) — каждое удобство галочкой
              ...(row.code === 'features'
                ? features.map(({ code, name }) => (
                    <tr
                      key={`feature-${code}`}
                      className="compare-table__row compare-table__row--feature"
                    >
                      <th scope="row" className={`${LABEL_CLASS} py-2 pl-5 font-normal`}>
                        {name}
                      </th>
                      {items.map((item) => {
                        const has = item.features.includes(code);
                        return (
                          <td key={item.listing.id} className={`${CELL_CLASS} py-2`}>
                            {has ? (
                              <Icon name="check" className="size-5 text-[var(--success-text)]" />
                            ) : (
                              <span className="text-[var(--text-secondary)]" aria-hidden="true">
                                —
                              </span>
                            )}
                            <span className="sr-only">{has ? ct.yes : ct.no}</span>
                          </td>
                        );
                      })}
                    </tr>
                  ))
                : []),
            ];
          })}
        </tbody>
      </table>
    </div>
  );
}
