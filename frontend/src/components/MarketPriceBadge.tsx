import { Link } from 'react-router-dom';
import type { ListingId, PriceEstimate } from '../api/types';
import { useApi } from '../hooks/useApi';
import { fill, formatPrice, plural } from '../lib/format';
import { isInTelegram } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

interface MarketPriceBadgeProps {
  listingId: ListingId;
}

type ShownLevel = 'below' | 'fair' | 'above';

const LEVEL_CLASS: Record<ShownLevel, string> = {
  below: 'bg-[var(--success-bg)] text-[var(--success-text)]',
  fair: 'bg-[var(--surface-hover)] text-[var(--text-secondary)]',
  above: 'bg-[var(--warning-bg)] text-[var(--warning-text)]',
};

const LEVEL_MARK: Record<ShownLevel, string> = { below: '↓', fair: '', above: '↑' };

function isShownLevel(level: string): level is ShownLevel {
  return level === 'below' || level === 'fair' || level === 'above';
}

/**
 * Плашка под ценой: «Ниже рынка» / «Обычная цена» / «Выше рынка». Оценку целиком считает
 * бэкенд — показываем его level как есть. С Premium — проценты и обычная цена, без него —
 * ссылка на Premium. Вне Telegram, пока грузится и при любой ошибке плашки нет.
 */
export default function MarketPriceBadge({ listingId }: MarketPriceBadgeProps) {
  const { lang, t } = useI18n();
  const pt = t.listing.market;
  // Без initData бэкенд ответит 401 — запрос не отправляем
  const { data } = useApi<PriceEstimate>(
    isInTelegram() ? `/api/listings/${encodeURIComponent(listingId)}/price` : null,
  );

  if (!data || !isShownLevel(data.level)) return null;

  const level = data.level;
  const byM2 = data.basis === 'district_m2';
  const percent =
    typeof data.diff_percent === 'number' ? Math.abs(Math.round(data.diff_percent)) : 0;
  const facts = [
    typeof data.typical_price === 'number'
      ? fill(pt.typical, formatPrice(data.typical_price, data.currency))
      : '',
    typeof data.sample === 'number' && data.sample > 0 ? plural(pt.sample, data.sample, lang) : '',
  ].filter(Boolean);

  let details = '';
  if (level === 'fair') {
    // У обычной цены процента нет: «Обычно 1 200 ₾, по 7 объявлениям»
    details = facts.length > 0 ? [...facts, byM2 ? pt.by_m2 : ''].filter(Boolean).join(', ') : '';
  } else if (percent > 0) {
    const diff = fill(
      pt[level === 'below' ? 'cheaper' : 'pricier'][byM2 ? 'm2' : 'rooms'],
      percent,
    );
    details = facts.length > 0 ? `${diff} (${facts.join(', ')})` : diff;
  } else {
    details = facts.join(', ');
  }

  return (
    <aside
      className={`market-price market-price--${level} flex flex-wrap items-center gap-x-3 gap-y-1.5`}
      aria-label={pt.label}
    >
      <p
        className={`market-price__badge m-0 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-semibold leading-5 ${LEVEL_CLASS[level]}`}
      >
        {LEVEL_MARK[level] && <span aria-hidden="true">{LEVEL_MARK[level]}</span>}
        {pt.levels[level]}
      </p>
      {data.premium_required && level !== 'fair' && (
        <Link
          to="/premium"
          className="market-price__premium rounded-[var(--radius-sm)] text-sm font-semibold text-[var(--text-primary)] underline underline-offset-2 transition-colors hover:text-[var(--primary)]"
        >
          {pt.how_much}
        </Link>
      )}
      {details && (
        <p className="market-price__details m-0 basis-full break-words text-sm leading-5 text-[var(--text-secondary)] first-letter:uppercase">
          {details}
        </p>
      )}
    </aside>
  );
}
