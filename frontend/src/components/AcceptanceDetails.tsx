import {
  ACCEPTANCE_ADDRESS_MAX,
  ACCEPTANCE_KEYS_MAX,
  ACCEPTANCE_METER_MAX,
  ACCEPTANCE_NAME_MAX,
  ACCEPTANCE_NOTES_MAX,
  acceptanceDate,
} from '../lib/acceptance';
import type { AcceptanceDraft, AcceptanceField } from '../lib/acceptance';
import { CONTRACT_LANGUAGES } from '../lib/contract';
import { useI18n } from '../providers/I18nProvider';
import FormField from './FormField';
import { FORM_LEGEND_CLASS } from './HotelFormMain';
import PillGroup from './PillGroup';
import TextAreaField from './TextAreaField';

const METERS = ['electricity', 'gas', 'water'] as const;

interface AcceptanceDetailsProps {
  draft: AcceptanceDraft;
  /** Адрес, который видит человек: свой или из объявления */
  address: string;
  /** Текст ошибки поля, если она есть */
  error: (field: AcceptanceField) => string | undefined;
  /** Идёт отправка: поля менять нельзя */
  disabled: boolean;
  onChange: (patch: Partial<AcceptanceDraft>) => void;
}

/** Данные акта приёмки под чек-листом: стороны, адрес, дата, ключи, счётчики, примечания, язык */
export default function AcceptanceDetails({
  draft,
  address,
  error,
  disabled,
  onChange,
}: AcceptanceDetailsProps) {
  const { t } = useI18n();
  const at = t.acceptance;
  const ct = t.contract;

  return (
    <fieldset
      className="acceptance-details m-0 flex min-w-0 flex-col gap-4 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[var(--shadow-sm)]"
      disabled={disabled}
    >
      <legend className="sr-only">{at.details}</legend>
      <FormField
        label={at.landlord}
        name="landlord_name"
        type="text"
        autoComplete="off"
        maxLength={ACCEPTANCE_NAME_MAX}
        value={draft.landlord_name}
        error={error('landlord_name')}
        onChange={(event) => onChange({ landlord_name: event.target.value })}
      />
      <FormField
        label={at.tenant}
        name="tenant_name"
        type="text"
        autoComplete="off"
        maxLength={ACCEPTANCE_NAME_MAX}
        value={draft.tenant_name}
        error={error('tenant_name')}
        onChange={(event) => onChange({ tenant_name: event.target.value })}
      />
      <FormField
        label={ct.address}
        name="address"
        type="text"
        autoComplete="off"
        maxLength={ACCEPTANCE_ADDRESS_MAX}
        value={address}
        error={error('address')}
        onChange={(event) => onChange({ address: event.target.value })}
      />
      <div className="acceptance-details__row grid grid-cols-2 gap-3">
        <FormField
          label={at.date}
          name="handover_date"
          type="date"
          value={acceptanceDate(draft)}
          error={error('handover_date')}
          onChange={(event) => onChange({ handover_date: event.target.value })}
        />
        <FormField
          label={at.keys}
          name="keys"
          type="number"
          inputMode="numeric"
          min={0}
          max={ACCEPTANCE_KEYS_MAX}
          value={draft.keys}
          error={error('keys')}
          onChange={(event) => onChange({ keys: event.target.value })}
        />
      </div>

      <fieldset className="acceptance-details__meters m-0 min-w-0 border-0 p-0">
        <legend className={FORM_LEGEND_CLASS}>
          {at.meters}{' '}
          <span className="font-normal text-[var(--text-secondary)]">· {ct.optional}</span>
        </legend>
        <div className="grid grid-cols-3 gap-3">
          {METERS.map((meter) => (
            <FormField
              key={meter}
              label={at[meter]}
              name={meter}
              type="text"
              inputMode="decimal"
              autoComplete="off"
              maxLength={ACCEPTANCE_METER_MAX}
              value={draft[meter]}
              error={error(meter)}
              onChange={(event) => onChange({ [meter]: event.target.value })}
            />
          ))}
        </div>
      </fieldset>

      <TextAreaField
        label={at.notes}
        name="notes"
        maxLength={ACCEPTANCE_NOTES_MAX}
        value={draft.notes}
        placeholder={at.notes_placeholder}
        hint={ct.optional}
        error={error('notes')}
        onChange={(event) => onChange({ notes: event.target.value })}
      />

      <PillGroup
        legend={at.second_language}
        legendClassName={FORM_LEGEND_CLASS}
        options={CONTRACT_LANGUAGES.map((value) => ({ value, label: ct.languages[value] }))}
        selected={[draft.second_language]}
        onToggle={(second_language) => onChange({ second_language })}
      />
      <p className="acceptance-details__language-hint -mt-2 text-xs text-[var(--text-secondary)]">
        {ct.second_language_hint}
      </p>
    </fieldset>
  );
}
