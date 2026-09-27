import { Link } from 'react-router-dom';
import { haptic } from '../lib/telegram';
import Icon from './Icon';
import type { IconName } from './Icon';

interface StatTileProps {
  icon: IconName;
  label: string;
  value: number | string;
  /** Пояснение рядом с подписью (например, «Скоро») */
  hint?: string;
  /** Плитка-ссылка: переход по нажатию */
  to?: string;
}

const TILE_CLASS =
  'stat-tile flex h-full flex-col gap-2 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[var(--shadow-sm)]';

/** Плитка статистики профиля: иконка, крупное число, подпись */
export default function StatTile({ icon, label, value, hint, to }: StatTileProps) {
  const content = (
    <>
      <span className="stat-tile__icon inline-grid size-9 place-items-center rounded-full bg-[var(--primary)]/10 text-[var(--primary)]">
        <Icon name={icon} />
      </span>
      <span className="stat-tile__value text-2xl font-bold leading-tight">{value}</span>
      <span className="stat-tile__label text-sm text-[var(--text-secondary)]">
        {label}
        {hint && <span className="stat-tile__hint"> · {hint}</span>}
      </span>
    </>
  );

  if (to) {
    return (
      <Link
        to={to}
        className={`${TILE_CLASS} hover:bg-[var(--surface-hover)] active:scale-[.98]`}
        onClick={() => haptic('light')}
      >
        {content}
      </Link>
    );
  }
  return <p className={TILE_CLASS}>{content}</p>;
}
