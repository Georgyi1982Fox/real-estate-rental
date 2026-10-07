import { fill } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

interface FilterButtonProps {
  /** Сколько фильтров выбрано: «Фильтры · 3» */
  count: number;
  onClick: () => void;
}

/** Кнопка «Фильтры» рядом со строкой поиска — открывает FilterModal */
export default function FilterButton({ count, onClick }: FilterButtonProps) {
  const { t } = useI18n();
  const ht = t.home;
  const active = count > 0;

  return (
    <button
      type="button"
      className={`filter-button inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center gap-2 rounded-[var(--radius-md)] border px-3 py-3 text-sm font-semibold shadow-[var(--shadow-sm)] transition-colors duration-200 hover:bg-[var(--surface-hover)] active:scale-[.98] sm:px-4 ${
        active
          ? 'border-[var(--primary)] bg-[var(--surface)] text-[var(--primary)]'
          : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)]'
      }`}
      aria-haspopup="dialog"
      aria-label={active ? fill(ht.filters_count, count) : ht.filters}
      onClick={() => {
        haptic('light');
        onClick();
      }}
    >
      <Icon name="sliders" className="size-5" />
      {/* На телефоне кнопка стоит в одном ряду с полем поиска: только значок и число */}
      <span className="hidden sm:inline">{active ? `${ht.filters} · ${count}` : ht.filters}</span>
      {active && <span className="sm:hidden">{count}</span>}
    </button>
  );
}
