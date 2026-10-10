import { fill } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

interface RatingStarsProps {
  /** Сколько звёзд у гостиницы: 1–5 */
  value: number;
  className?: string;
}

/** Звёзды гостиницы: столько значков, сколько звёзд; для скринридера — «Звёзд: 4» */
export default function RatingStars({ value, className = 'size-4' }: RatingStarsProps) {
  const { t } = useI18n();
  const count = Math.min(5, Math.max(0, Math.round(value)));

  if (count === 0) return null;

  return (
    <span
      className="rating-stars inline-flex shrink-0 items-center gap-0.5 text-[var(--star)]"
      role="img"
      aria-label={fill(t.hotels.stars_label, count)}
    >
      {Array.from({ length: count }, (_, index) => (
        <Icon key={index} name="star" className={`fill-current ${className}`} />
      ))}
    </span>
  );
}
