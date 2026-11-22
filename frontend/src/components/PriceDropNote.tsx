import type { Listing } from '../api/types';
import { fillVars, formatPrice, timeAgo } from '../lib/format';
import { priceDrop } from '../lib/priceDrop';
import { useI18n } from '../providers/I18nProvider';
import PriceDropBadge from './PriceDropBadge';

interface PriceDropNoteProps {
  listing: Pick<Listing, 'price' | 'currency' | 'old_price' | 'price_dropped_at'>;
}

/**
 * Под ценой на странице квартиры (FRONTEND-055): «📉 Цена снижена 3 дня назад: было 1 500 $».
 * Повод написать хозяину и поторговаться. Цена не снижалась за 30 дней — ничего
 */
export default function PriceDropNote({ listing }: PriceDropNoteProps) {
  const { lang, t } = useI18n();
  const drop = priceDrop(listing);
  if (!drop) return null;
  const when = drop.droppedAt ? timeAgo(drop.droppedAt, lang) : '';
  // Даты нет (или она не читается) — хотя бы зачёркнутая цена и процент, как в карточке
  if (!when) return <PriceDropBadge listing={listing} className="listing-price-drop" />;

  return (
    <p className="listing-price-drop m-0 inline-flex items-start gap-2 rounded-[var(--radius-md)] bg-[var(--success-bg)] px-3 py-2 text-sm font-medium text-[var(--success-text)]">
      <span aria-hidden="true">📉</span>
      <span>
        {fillVars(t.price_drop.page, {
          when,
          // «850 ₾» не разрывается между строками
          old: formatPrice(drop.oldPrice, listing.currency).replace(/\s/g, ' '),
        })}
      </span>
    </p>
  );
}
