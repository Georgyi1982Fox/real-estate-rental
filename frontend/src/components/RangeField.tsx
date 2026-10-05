import { useEffect, useId, useState } from 'react';
import type { KeyboardEvent } from 'react';

const DEBOUNCE_MS = 400;
// В type="number" браузер пропускает e, знаки и дроби — значение только целое и положительное
const BLOCKED_KEYS = new Set(['e', 'E', '+', '-', '.', ',']);

type Field = 'min' | 'max';

interface Hint {
  field: Field;
  kind: 'order' | 'limit';
}

interface RangeFieldProps {
  /** Подпись поля: «Цена, ₾/мес.», «Площадь, м²» */
  label: string;
  /** Подписи границ для скринридера */
  minLabel: string;
  maxLabel: string;
  /** Атрибуты name полей — как параметры API: min_price / max_price */
  names: Record<Field, string>;
  min?: number;
  max?: number;
  /** Наименьшее и наибольшее допустимое значение */
  lowest?: number;
  limit: number;
  step?: number;
  /** Подсказки: минимум больше максимума, максимум меньше минимума, значение больше limit */
  errors: { min: string; max: string; limit: string };
  /** Вызывается только с корректной парой (min ≤ max ≤ limit) */
  onChange: (min: number | undefined, max: number | undefined) => void;
  inputClassName: string;
  labelClassName?: string;
}

const toText = (value?: number) => (value === undefined ? '' : String(value));
const toNumber = (text: string) => (text === '' ? undefined : Number(text));

/** Что не так с парой после правки поля field; null — всё верно */
function validate(
  min: number | undefined,
  max: number | undefined,
  field: Field,
  lowest: number,
  limit: number,
): Hint | null {
  const value = field === 'min' ? min : max;
  if (value !== undefined && (value > limit || value < lowest)) return { field, kind: 'limit' };
  if (min !== undefined && max !== undefined && min > max) return { field, kind: 'order' };
  return null;
}

/**
 * Числовой диапазон «от — до». Значение уходит в фильтр через 400 мс после ввода и только
 * корректное: минимум не больше максимума и наоборот. Неверный ввод — красная подсказка,
 * а при уходе из поля в нём возвращается последнее верное значение.
 */
export default function RangeField({
  label,
  minLabel,
  maxLabel,
  names,
  min,
  max,
  lowest = 0,
  limit,
  step = 1,
  errors,
  onChange,
  inputClassName,
  labelClassName = 'text-xs font-medium text-[var(--text-secondary)]',
}: RangeFieldProps) {
  const id = useId();
  const [text, setText] = useState({ min: toText(min), max: toText(max) });
  const [edited, setEdited] = useState<Field | null>(null);
  const [hint, setHint] = useState<Hint | null>(null);
  const [applied, setApplied] = useState({ min, max });

  // Фильтр изменился снаружи («Сбросить», переход из сохранённого поиска) — показываем его
  if (applied.min !== min || applied.max !== max) {
    setApplied({ min, max });
    setText({ min: toText(min), max: toText(max) });
    setEdited(null);
    setHint(null);
  }

  useEffect(() => {
    if (!edited) return;
    const timer = window.setTimeout(() => {
      const nextMin = toNumber(text.min);
      const nextMax = toNumber(text.max);
      const problem = validate(nextMin, nextMax, edited, lowest, limit);
      setHint(problem);
      if (!problem && (nextMin !== min || nextMax !== max)) onChange(nextMin, nextMax);
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [text, edited, min, max, lowest, limit, onChange]);

  const change = (field: Field, value: string) => {
    setText((current) => ({ ...current, [field]: value }));
    setEdited(field);
  };

  const blur = (field: Field) => {
    const problem = validate(toNumber(text.min), toNumber(text.max), field, lowest, limit);
    if (!problem) return;
    // Неверное значение в поле не остаётся: возвращаем последнее применённое
    setHint(problem);
    setText((current) => ({ ...current, [field]: toText(field === 'min' ? min : max) }));
    setEdited(null);
  };

  const blockKeys = (event: KeyboardEvent<HTMLInputElement>) => {
    if (BLOCKED_KEYS.has(event.key)) event.preventDefault();
  };

  const message = !hint ? '' : hint.kind === 'limit' ? errors.limit : errors[hint.field];

  const invalidClass = 'border-[var(--danger)] ring-1 ring-[var(--danger)]';

  const input = (field: Field) => {
    const invalid = hint?.field === field;
    return (
      <input
        id={`${id}-${field}`}
        name={names[field]}
        type="number"
        inputMode="numeric"
        // Стрелки и колесо мыши не дают перейти через соседнее поле
        min={field === 'min' ? lowest : (min ?? lowest)}
        max={field === 'min' ? (max ?? limit) : limit}
        step={step}
        placeholder={field === 'min' ? String(lowest) : String(limit)}
        value={text[field]}
        aria-invalid={invalid}
        aria-describedby={invalid ? `${id}-hint` : undefined}
        onChange={(event) => change(field, event.target.value)}
        onBlur={() => blur(field)}
        onKeyDown={blockKeys}
        className={`${inputClassName} w-24 px-2 py-2 ${invalid ? invalidClass : ''}`}
      />
    );
  };

  return (
    <div className="range-field flex min-w-0 flex-col gap-1">
      <span className={labelClassName} id={`${id}-label`}>
        {label}
      </span>
      <div className="flex items-center gap-2" role="group" aria-labelledby={`${id}-label`}>
        <label className="sr-only" htmlFor={`${id}-min`}>
          {minLabel}
        </label>
        {input('min')}
        <span className="text-[var(--text-secondary)]" aria-hidden="true">
          —
        </span>
        <label className="sr-only" htmlFor={`${id}-max`}>
          {maxLabel}
        </label>
        {input('max')}
      </div>
      {message && (
        <p
          id={`${id}-hint`}
          role="alert"
          className="range-field__hint max-w-56 text-xs font-medium text-[var(--danger)]"
        >
          {message}
        </p>
      )}
    </div>
  );
}
