import { useI18n } from '../providers/I18nProvider';

export type PriceLevel = 'below' | 'fair' | 'above';

const LEVEL_CLASS: Record<PriceLevel, string> = {
  below: 'bg-[var(--success-bg)] text-[var(--success-text)]',
  fair: 'bg-[var(--surface-hover)] text-[var(--text-secondary)]',
  above: 'bg-[var(--warning-bg)] text-[var(--warning-text)]',
};

const LEVEL_MARK: Record<PriceLevel, string> = { below: '↓', fair: '', above: '↑' };

/** Уровень, для которого есть плашка; unknown и незнакомые значения не показываем */
export function isPriceLevel(level: string): level is PriceLevel {
  return level === 'below' || level === 'fair' || level === 'above';
}

interface PriceLevelBadgeProps {
  level: PriceLevel;
  className?: string;
}

/** Плашка «↓ Ниже рынка» / «Обычная цена» / «↑ Выше рынка» (объявление и сравнение) */
export default function PriceLevelBadge({ level, className = '' }: PriceLevelBadgeProps) {
  const { t } = useI18n();

  return (
    <p
      className={`market-price__badge m-0 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-semibold leading-5 ${LEVEL_CLASS[level]} ${className}`}
    >
      {LEVEL_MARK[level] && <span aria-hidden="true">{LEVEL_MARK[level]}</span>}
      {t.listing.market.levels[level]}
    </p>
  );
}
