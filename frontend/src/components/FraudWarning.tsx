import type { FraudLevel } from '../api/types';
import { fraudReasonTexts } from '../lib/fraud';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

interface FraudWarningProps {
  level: FraudLevel;
  reasons: string[];
}

/** Блок-предупреждение на странице объявления: warning — жёлтый, high — красный */
export default function FraudWarning({ level, reasons }: FraudWarningProps) {
  const { t } = useI18n();
  const ft = t.listing.fraud;

  if (level === 'none') return null;

  const isHigh = level === 'high';
  const items = fraudReasonTexts(reasons, ft.reasons);

  return (
    <aside
      className={`fraud-warning fraud-warning--${level} flex gap-3 rounded-[var(--radius-md)] border p-4 text-sm leading-5 ${
        isHigh
          ? 'border-[var(--danger-border)] bg-[var(--danger-bg)] text-[var(--danger-text)]'
          : 'border-[var(--warning-border)] bg-[var(--warning-bg)] text-[var(--warning-text)]'
      }`}
      aria-labelledby="fraud-warning-title"
    >
      <Icon name={isHigh ? 'ban' : 'alert'} className="fraud-warning__icon mt-0.5 size-5" />
      <div className="fraud-warning__body min-w-0 space-y-2 break-words">
        <h2
          id="fraud-warning-title"
          className="fraud-warning__title text-base font-semibold leading-6"
        >
          {isHigh ? ft.high : ft.warning}
        </h2>
        <p className="fraud-warning__advice">{ft.advice}</p>
        {items.length > 0 && (
          <ul
            className="fraud-warning__reasons list-disc space-y-1 pl-5"
            aria-label={ft.reasons_label}
          >
            {items.map((text) => (
              <li key={text}>{text}</li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
