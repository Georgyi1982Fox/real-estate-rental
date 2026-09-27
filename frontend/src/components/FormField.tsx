import { useId } from 'react';
import type { InputHTMLAttributes } from 'react';

interface FormFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'className' | 'id'> {
  label: string;
  hint?: string;
}

/** Поле формы: подпись + input + подсказка (связаны через id/aria-describedby) */
export default function FormField({ label, hint, ...inputProps }: FormFieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;

  return (
    <p className="form-field m-0 flex flex-col gap-1.5">
      <label htmlFor={id} className="form-field__label text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        aria-describedby={hintId}
        className="form-field__input min-h-12 w-full min-w-0 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-base text-[var(--text-primary)] transition-colors duration-200 placeholder:text-[var(--text-secondary)] hover:border-[var(--text-secondary)] focus:border-[var(--primary)]"
        {...inputProps}
      />
      {hint && (
        <small id={hintId} className="form-field__hint text-xs text-[var(--text-secondary)]">
          {hint}
        </small>
      )}
    </p>
  );
}
