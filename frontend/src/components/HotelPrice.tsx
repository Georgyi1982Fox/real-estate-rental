import { fill, formatPrice } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';

interface HotelPriceProps {
  /** Цена самого дешёвого номера за ночь; null — номеров ещё нет, цены не показываем */
  price: number | null | undefined;
  className: string;
  /** Размер и цвет приписки «/ ночь» */
  periodClassName: string;
}

/** Цена гостиницы: «от 120 ₾ / ночь» */
export default function HotelPrice({ price, className, periodClassName }: HotelPriceProps) {
  const { t } = useI18n();

  if (typeof price !== 'number') return null;

  return (
    <p className={className}>
      {fill(t.hotels.from_price, formatPrice(price))}{' '}
      <span className={`whitespace-nowrap ${periodClassName}`}>{t.hotels.per_night}</span>
    </p>
  );
}
