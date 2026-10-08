import type { RentPeriod } from '../api/types';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

const PERIODS: RentPeriod[] = ['monthly', 'daily'];

interface RentPeriodToggleProps {
  value: RentPeriod;
  onChange: (period: RentPeriod) => void;
  /** На всю ширину (окно фильтров); по умолчанию — по ширине подписей */
  wide?: boolean;
}

/** Переключатель «Помесячно / Посуточно»: выбран всегда ровно один срок аренды */
export default function RentPeriodToggle({ value, onChange, wide }: RentPeriodToggleProps) {
  const { t } = useI18n();
  const ft = t.filters;

  return (
    <fieldset
      className={`rent-period min-w-0 max-w-full rounded-full border border-[var(--border)] bg-[var(--surface)] p-1 shadow-[var(--shadow-sm)] ${wide ? 'flex' : 'inline-flex'}`}
    >
      <legend className="sr-only">{ft.rent_period}</legend>
      {PERIODS.map((period) => {
        const active = period === value;
        return (
          <button
            key={period}
            type="button"
            className={`rent-period__option inline-flex min-h-9 min-w-0 items-center justify-center rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors duration-200 active:scale-[.98] ${wide ? 'flex-1' : ''} ${
              active
                ? 'bg-[var(--primary)] text-white'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
            aria-pressed={active}
            onClick={() => {
              if (active) return;
              haptic('selection');
              onChange(period);
            }}
          >
            {ft[period]}
          </button>
        );
      })}
    </fieldset>
  );
}
