import { useEffect, useId, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { fill, formatPrice } from '../lib/format';
import { PRICE_MAX, PRICE_STEP } from '../lib/searchFilters';
import { useI18n } from '../providers/I18nProvider';

const DEBOUNCE_MS = 400;
// В type="number" браузер пропускает e, знаки и дроби — цена только целая и положительная
const BLOCKED_KEYS = new Set(['e', 'E', '+', '-', '.', ',']);

type Field = 'min' | 'max';

interface Hint {
  field: Field;
  kind: 'order' | 'limit';
}

interface PriceRangeProps {
  min?: number;
  max?: number;
  /** Вызывается только с корректной парой (min ≤ max ≤ PRICE_MAX) */
  onChange: (min: number | undefined, max: number | undefined) => void;
  inputClassName: string;
  /** Подпись «Цена»: по умолчанию мелкая, в окне фильтров — как заголовки остальных полей */
  labelClassName?: string;
}

const toText = (value?: number) => (value === undefined ? '' : String(value));
const toNumber = (text: string) => (text === '' ? undefined : Number(text));

/** Что не так с парой цен после правки поля field; null — всё верно */
function validate(min: number | undefined, max: number | undefined, field: Field): Hint | null {
  const value = field === 'min' ? min : max;
  if (value !== undefined && value > PRICE_MAX) return { field, kind: 'limit' };
  if (min !== undefined && max !== undefined && min > max) return { field, kind: 'order' };
  return null;
}

/**
 * Цена «от — до». Значение уходит в фильтр через 400 мс после ввода и только корректное:
 * минимум не больше максимума и наоборот. Неверный ввод — красная подсказка,
 * а при уходе из поля в нём возвращается последнее верное значение.
 */
export default function PriceRange({
  min,
  max,
  onChange,
  inputClassName,
  labelClassName = 'text-xs font-medium text-[var(--text-secondary)]',
}: PriceRangeProps) {
  const { t } = useI18n();
  const ht = t.home;
  const hintId = useId();
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
      const problem = validate(nextMin, nextMax, edited);
      setHint(problem);
      if (!problem && (nextMin !== min || nextMax !== max)) onChange(nextMin, nextMax);
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [text, edited, min, max, onChange]);

  const change = (field: Field, value: string) => {
    setText((current) => ({ ...current, [field]: value }));
    setEdited(field);
  };

  const blur = (field: Field) => {
    const problem = validate(toNumber(text.min), toNumber(text.max), field);
    if (!problem) return;
    // Неверное значение в поле не остаётся: возвращаем последнее применённое
    setHint(problem);
    setText((current) => ({ ...current, [field]: toText(field === 'min' ? min : max) }));
    setEdited(null);
  };

  const blockKeys = (event: KeyboardEvent<HTMLInputElement>) => {
    if (BLOCKED_KEYS.has(event.key)) event.preventDefault();
  };

  const message = !hint
    ? ''
    : hint.kind === 'limit'
      ? fill(ht.price_limit_error, formatPrice(PRICE_MAX))
      : hint.field === 'min'
        ? ht.price_min_error
        : ht.price_max_error;

  const invalidClass = 'border-[var(--danger)] ring-1 ring-[var(--danger)]';

  const input = (field: Field) => {
    const invalid = hint?.field === field;
    return (
      <input
        id={`filter-price-${field}`}
        name={`${field}_price`}
        type="number"
        inputMode="numeric"
        // Стрелки и колесо мыши не дают перейти через соседнее поле
        min={field === 'min' ? 0 : (min ?? 0)}
        max={field === 'min' ? (max ?? PRICE_MAX) : PRICE_MAX}
        step={PRICE_STEP}
        placeholder={field === 'min' ? '0' : String(PRICE_MAX)}
        value={text[field]}
        aria-invalid={invalid}
        aria-describedby={invalid ? hintId : undefined}
        onChange={(event) => change(field, event.target.value)}
        onBlur={() => blur(field)}
        onKeyDown={blockKeys}
        className={`${inputClassName} w-24 px-2 py-2 ${invalid ? invalidClass : ''}`}
      />
    );
  };

  return (
    <div className="price-range flex min-w-0 flex-col gap-1">
      <span className={labelClassName} id="price-range-label">
        {ht.price}
      </span>
      <div className="flex items-center gap-2" role="group" aria-labelledby="price-range-label">
        <label className="sr-only" htmlFor="filter-price-min">
          {ht.price_min}
        </label>
        {input('min')}
        <span className="text-[var(--text-secondary)]" aria-hidden="true">
          —
        </span>
        <label className="sr-only" htmlFor="filter-price-max">
          {ht.price_max}
        </label>
        {input('max')}
      </div>
      {message && (
        <p
          id={hintId}
          role="alert"
          className="price-range__hint max-w-56 text-xs font-medium text-[var(--danger)]"
        >
          {message}
        </p>
      )}
    </div>
  );
}
