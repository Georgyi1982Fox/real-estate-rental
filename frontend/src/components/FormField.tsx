import { useId } from 'react';
import type { InputHTMLAttributes } from 'react';

interface FormFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'className' | 'id'> {
  label: string;
  hint?: string;
  /** Что не так с полем: красная рамка и текст вместо подсказки */
  error?: string;
}

export const FIELD_INPUT_CLASS =
  'form-field__input w-full min-w-0 rounded-[var(--radius-md)] border bg-[var(--surface)] px-4 py-3 text-base text-[var(--text-primary)] transition-colors duration-200 placeholder:text-[var(--text-secondary)]';
/** Рамка поля: обычная или красная, если в нём ошибка */
export function fieldBorderClass(invalid: boolean): string {
  return invalid
    ? 'border-[var(--danger)]'
    : 'border-[var(--border)] hover:border-[var(--text-secondary)] focus:border-[var(--primary)]';
}
export const FIELD_ERROR_CLASS = 'form-field__error text-xs font-medium text-[var(--danger)]';

/** Поле формы: подпись + input + подсказка или ошибка (связаны через id/aria-describedby) */
export default function FormField({ label, hint, error, ...inputProps }: FormFieldProps) {
  const id = useId();
  const note = error || hint;
  const noteId = note ? `${id}-hint` : undefined;

  return (
    <p className="form-field m-0 flex min-w-0 flex-col gap-1.5">
      <label htmlFor={id} className="form-field__label text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        aria-describedby={noteId}
        aria-invalid={error ? true : undefined}
        className={`${FIELD_INPUT_CLASS} min-h-12 ${fieldBorderClass(Boolean(error))}`}
        {...inputProps}
      />
      {note && (
        <small
          id={noteId}
          className={
            error ? FIELD_ERROR_CLASS : 'form-field__hint text-xs text-[var(--text-secondary)]'
          }
        >
          {note}
        </small>
      )}
    </p>
  );
}
