import type { RepairLevel } from '../api/types';
import { useI18n } from '../providers/I18nProvider';

const LEVEL_CLASS: Record<RepairLevel, string> = {
  excellent: 'bg-[var(--success-bg)] text-[var(--success-text)]',
  good: 'bg-[var(--surface-hover)] text-[var(--text-secondary)]',
  needs_repair: 'bg-[var(--promo-bg)] text-[var(--promo-text)]',
};

/** Уровень, для которого есть значок; null и незнакомые значения не показываем */
export function isRepairLevel(level: unknown): level is RepairLevel {
  return level === 'excellent' || level === 'good' || level === 'needs_repair';
}

interface RepairBadgeProps {
  level: RepairLevel;
  /** Мелкая подпись «по фото, оценка AI» рядом со значком */
  hint?: boolean;
  className?: string;
}

/**
 * Значок «🛠 Отличный ремонт» (зелёный) / «Хороший ремонт» (нейтральный) /
 * «Нужен ремонт» (оранжевый). Текст — из наших строк, на языке интерфейса
 */
export default function RepairBadge({ level, hint = true, className = '' }: RepairBadgeProps) {
  const { t } = useI18n();
  const rt = t.listing.repair;

  return (
    <p
      className={`repair-badge repair-badge--${level} m-0 flex flex-wrap items-center gap-x-2 gap-y-0.5 ${className}`}
    >
      <span
        className={`repair-badge__level inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold leading-5 ${LEVEL_CLASS[level]}`}
      >
        <span aria-hidden="true">🛠</span>
        {rt.levels[level]}
      </span>
      {hint && (
        <span className="repair-badge__hint text-xs text-[var(--text-secondary)]">{rt.hint}</span>
      )}
    </p>
  );
}
