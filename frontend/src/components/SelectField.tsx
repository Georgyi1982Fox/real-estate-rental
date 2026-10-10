import { useId } from 'react';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectFieldProps {
  label: string;
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  /** Первая пустая строка («Выберите…»); без неё выбрано всегда одно из значений */
  placeholder?: string;
  name?: string;
}

/** Поле формы с выпадающим списком: подпись + нативный select (в стиле FormField) */
export default function SelectField({
  label,
  value,
  options,
  onChange,
  placeholder,
  name,
}: SelectFieldProps) {
  const id = useId();

  return (
    <p className="form-field m-0 flex min-w-0 flex-col gap-1.5">
      <label htmlFor={id} className="form-field__label text-sm font-medium">
        {label}
      </label>
      <select
        id={id}
        name={name}
        value={value}
        className="form-field__input min-h-12 w-full min-w-0 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-3 text-base text-[var(--text-primary)] transition-colors duration-200 hover:border-[var(--text-secondary)] focus:border-[var(--primary)]"
        onChange={(event) => onChange(event.target.value)}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </p>
  );
}
