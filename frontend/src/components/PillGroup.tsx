import { haptic } from '../lib/telegram';

/** Кнопка-«таблетка»: выбранная закрашена основным цветом */
export function pillClass(selected: boolean): string {
  const state = selected
    ? 'border-[var(--primary)] bg-[var(--primary)] text-white'
    : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--surface-hover)]';
  return `pill-group__pill inline-flex min-h-10 items-center justify-center rounded-full border px-3.5 py-2 text-sm font-medium transition-colors duration-200 active:scale-[.97] ${state}`;
}

interface PillOption<Value> {
  value: Value;
  label: string;
}

interface PillGroupProps<Value extends string | number> {
  legend: string;
  legendClassName: string;
  options: PillOption<Value>[];
  /** Выбранные значения: одно (комнаты) или несколько (удобства) */
  selected: Value[];
  /** Нажатие на таблетку; снять или добавить выбор решает родитель */
  onToggle: (value: Value) => void;
  /** Короткие подписи («1», «4+») — таблетки одной ширины */
  compact?: boolean;
  className?: string;
}

/** Группа кнопок-«таблеток» с заголовком: выбор одного или нескольких значений фильтра */
export default function PillGroup<Value extends string | number>({
  legend,
  legendClassName,
  options,
  selected,
  onToggle,
  compact,
  className = '',
}: PillGroupProps<Value>) {
  return (
    <fieldset className={`pill-group min-w-0 border-0 p-0 ${className}`}>
      <legend className={legendClassName}>{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map(({ value, label }) => {
          const active = selected.includes(value);
          return (
            <button
              key={value}
              type="button"
              className={`${pillClass(active)} ${compact ? 'min-w-12' : ''}`}
              aria-pressed={active}
              onClick={() => {
                haptic('selection');
                onToggle(value);
              }}
            >
              {label}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
