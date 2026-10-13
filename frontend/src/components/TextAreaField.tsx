import { useId } from 'react';
import type { TextareaHTMLAttributes } from 'react';
import { FIELD_ERROR_CLASS, FIELD_INPUT_CLASS, fieldBorderClass } from './FormField';

interface TextAreaFieldProps extends Omit<
  TextareaHTMLAttributes<HTMLTextAreaElement>,
  'className' | 'id' | 'value' | 'maxLength'
> {
  label: string;
  value: string;
  /** Предел длины: под полем — счётчик «12 / 500» */
  maxLength: number;
  hint?: string;
  /** Что не так с полем: красная рамка и текст вместо подсказки */
  error?: string;
}

/** Многострочное поле формы: подпись + textarea + подсказка или ошибка и счётчик символов */
export default function TextAreaField({
  label,
  value,
  maxLength,
  hint,
  error,
  rows = 3,
  ...areaProps
}: TextAreaFieldProps) {
  const id = useId();

  return (
    <p className="form-field m-0 flex min-w-0 flex-col gap-1.5">
      <label htmlFor={id} className="form-field__label text-sm font-medium">
        {label}
      </label>
      <textarea
        id={id}
        rows={rows}
        maxLength={maxLength}
        value={value}
        aria-describedby={`${id}-hint`}
        aria-invalid={error ? true : undefined}
        className={`${FIELD_INPUT_CLASS} resize-y leading-relaxed ${fieldBorderClass(Boolean(error))}`}
        {...areaProps}
      />
      <small
        id={`${id}-hint`}
        className="form-field__hint flex justify-between gap-3 text-xs text-[var(--text-secondary)]"
      >
        <span className={error ? FIELD_ERROR_CLASS : ''}>{error ?? hint}</span>
        <span className="shrink-0 tabular-nums">
          {value.length} / {maxLength}
        </span>
      </small>
    </p>
  );
}
