import { useId } from 'react';
import { fill } from '../lib/format';
import { HOTEL_DESCRIPTION_MAX, HOTEL_DESCRIPTION_MIN } from '../lib/hotelForm';
import { useI18n } from '../providers/I18nProvider';
import type { HotelFormStepProps } from './HotelFormMain';

/** Шаг 4 формы размещения: описание на любом языке, от 30 знаков, без ссылок и контактов */
export default function HotelFormDescription({ draft, onChange }: HotelFormStepProps) {
  const { t } = useI18n();
  const id = useId();
  const length = draft.description.trim().length;

  return (
    <p className="form-field m-0 flex flex-col gap-1.5">
      <label htmlFor={id} className="form-field__label text-sm font-medium">
        {t.listing.description}
      </label>
      <textarea
        id={id}
        name="description"
        rows={8}
        maxLength={HOTEL_DESCRIPTION_MAX}
        aria-describedby={`${id}-hint`}
        value={draft.description}
        className="form-field__input w-full min-w-0 resize-y rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-base leading-relaxed text-[var(--text-primary)] transition-colors duration-200 hover:border-[var(--text-secondary)] focus:border-[var(--primary)]"
        onChange={(event) => onChange({ description: event.target.value })}
      />
      <small
        id={`${id}-hint`}
        className="form-field__hint flex justify-between gap-3 text-xs text-[var(--text-secondary)]"
      >
        <span>{fill(t.hotel_form.description_hint, HOTEL_DESCRIPTION_MIN)}</span>
        <span
          className={`shrink-0 tabular-nums ${length < HOTEL_DESCRIPTION_MIN ? 'text-[var(--danger)]' : ''}`}
        >
          {length} / {HOTEL_DESCRIPTION_MAX}
        </span>
      </small>
    </p>
  );
}
