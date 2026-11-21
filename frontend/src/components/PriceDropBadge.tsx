import type { Listing } from '../api/types';
import { fill, formatPrice } from '../lib/format';
import { priceDrop } from '../lib/priceDrop';
import { useI18n } from '../providers/I18nProvider';

interface PriceDropBadgeProps {
  listing: Pick<Listing, 'price' | 'currency' | 'old_price' | 'price_dropped_at'>;
  /** Классы обёртки: отступы, место в строке */
  className?: string;
  /** Размер зачёркнутой цены */
  oldClassName?: string;
}

/**
 * Рядом с ценой в карточке (FRONTEND-055): прежняя цена зачёркнута и значок «📉 −13%».
 * Цена не снижалась за 30 дней — ничего
 */
export default function PriceDropBadge({
  listing,
  className = '',
  oldClassName = 'text-sm',
}: PriceDropBadgeProps) {
  const { t } = useI18n();
  const drop = priceDrop(listing);
  if (!drop) return null;

  return (
    <span className={`price-drop inline-flex flex-wrap items-center gap-x-2 gap-y-1 ${className}`}>
      <s className={`price-drop__old whitespace-nowrap text-[var(--text-secondary)] ${oldClassName}`}>
        <span className="sr-only">{t.price_drop.was} </span>
        {formatPrice(drop.oldPrice, listing.currency)}
      </s>
      {drop.percent > 0 && (
        <span
          className="price-drop__badge inline-flex items-center gap-1 whitespace-nowrap rounded-full bg-[var(--success-bg)] px-2 py-0.5 text-xs font-semibold leading-5 text-[var(--success-text)]"
          title={fill(t.price_drop.badge, drop.percent)}
        >
          <span aria-hidden="true">📉 −{drop.percent}%</span>
          <span className="sr-only">{fill(t.price_drop.badge, drop.percent)}</span>
        </span>
      )}
    </span>
  );
}
