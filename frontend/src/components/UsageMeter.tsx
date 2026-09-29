import { useId } from 'react';
import { fillVars } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';

interface UsageMeterProps {
  label: string;
  used: number;
  /** null — без ограничения (полоска не нужна) */
  limit: number | null;
}

/** «Избранное: 3 из 20» с полоской заполнения; лимит исчерпан — полоска золотая */
export default function UsageMeter({ label, used, limit }: UsageMeterProps) {
  const { t } = useI18n();
  const pt = t.premium;
  const labelId = useId();
  const full = limit !== null && used >= limit;
  const value =
    limit === null
      ? fillVars(pt.usage_unlimited, { used })
      : fillVars(pt.usage_of, { used, limit });

  return (
    <li className="usage-meter flex flex-col gap-2">
      <p className="usage-meter__row flex items-baseline justify-between gap-3 text-sm">
        <span id={labelId} className="text-[var(--text-secondary)]">
          {label}
        </span>
        <span className="font-semibold">{value}</span>
      </p>
      {limit !== null && (
        <progress
          className={`usage-meter__bar ${full ? 'usage-meter__bar--full' : ''}`}
          aria-labelledby={labelId}
          value={Math.min(used, limit)}
          max={Math.max(limit, 1)}
        >
          {value}
        </progress>
      )}
    </li>
  );
}
