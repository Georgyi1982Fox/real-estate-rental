import type { Listing } from '../api/types';
import { formatPrice } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';

interface ListingPriceProps {
  listing: Pick<Listing, 'price' | 'currency' | 'rent_period'>;
  className: string;
  /** Размер и цвет приписки «/ сутки» */
  periodClassName: string;
  /** Показывать и «/ мес.» у помесячной аренды; «/ сутки» у посуточной видна всегда */
  monthly?: boolean;
}

/** Цена объявления: «1 200 ₾», у посуточной аренды — «90 ₾ / сутки» */
export default function ListingPrice({
  listing,
  className,
  periodClassName,
  monthly,
}: ListingPriceProps) {
  const { t } = useI18n();
  const daily = listing.rent_period === 'daily';
  const period = daily ? t.listing.per_day : monthly ? t.listing.per_month : '';

  return (
    <p className={className}>
      {formatPrice(listing.price, listing.currency)}
      {period && (
        <>
          {' '}
          <span className={`whitespace-nowrap ${periodClassName}`}>{period}</span>
        </>
      )}
    </p>
  );
}
