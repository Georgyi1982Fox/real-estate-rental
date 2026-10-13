import type { FormEvent } from 'react';
import type { Currency } from '../api/types';
import {
  CONTRACT_ADDRESS_MAX,
  CONTRACT_CURRENCIES,
  CONTRACT_ID_MAX,
  CONTRACT_LANGUAGES,
  CONTRACT_MONEY_MAX,
  CONTRACT_MONTHS_MAX,
  CONTRACT_MONTHS_PRESETS,
  CONTRACT_NAME_MAX,
  CONTRACT_NOTES_MAX,
  CONTRACT_PAYMENT_DAY_MAX,
  CONTRACT_UTILITIES,
  contractDeposit,
} from '../lib/contract';
import type { ContractDraft, ContractErrors, ContractField } from '../lib/contract';
import { fill } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import FormField from './FormField';
import { FORM_LEGEND_CLASS } from './HotelFormMain';
import PillGroup from './PillGroup';
import SelectField from './SelectField';
import Switch from './Switch';
import TextAreaField from './TextAreaField';

const CURRENCY_LABELS: Record<Currency, string> = { GEL: '₾ GEL', USD: '$ USD', EUR: '€ EUR' };
const PARTY_CLASS = 'contract-form__party m-0 flex min-w-0 flex-col gap-3 border-0 p-0';
const PARTY_LEGEND_CLASS = 'mb-3 p-0 text-base font-semibold text-[var(--text-primary)]';

interface ContractFormProps {
  /** id формы: кнопка «Получить договор» живёт в футере окна, вне <form> */
  id: string;
  draft: ContractDraft;
  errors: ContractErrors;
  /** Идёт отправка: поля менять нельзя */
  disabled: boolean;
  onChange: (patch: Partial<ContractDraft>) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

/**
 * Анкета договора аренды: стороны, адрес, срок, плата, условия и второй язык.
 * Один экран с прокруткой; поля с ошибкой подсвечены
 */
export default function ContractForm({
  id,
  draft,
  errors,
  disabled,
  onChange,
  onSubmit,
}: ContractFormProps) {
  const { t } = useI18n();
  const ct = t.contract;
  const error = (field: ContractField) => {
    const problem = errors[field];
    return problem ? ct.errors[problem] : undefined;
  };
  const months = Number(draft.months);

  return (
    <form id={id} className="contract-form flex flex-col gap-5" noValidate onSubmit={onSubmit}>
      <p className="contract-form__intro m-0 text-sm text-[var(--text-secondary)]">{ct.intro}</p>

      <fieldset className={PARTY_CLASS} disabled={disabled}>
        <legend className={PARTY_LEGEND_CLASS}>{ct.landlord}</legend>
        <FormField
          label={ct.name}
          name="landlord_name"
          type="text"
          autoComplete="off"
          maxLength={CONTRACT_NAME_MAX}
          value={draft.landlord_name}
          error={error('landlord_name')}
          onChange={(event) => onChange({ landlord_name: event.target.value })}
        />
        <FormField
          label={ct.person_id}
          name="landlord_id"
          type="text"
          autoComplete="off"
          maxLength={CONTRACT_ID_MAX}
          value={draft.landlord_id}
          hint={ct.optional}
          error={error('landlord_id')}
          onChange={(event) => onChange({ landlord_id: event.target.value })}
        />
      </fieldset>

      <fieldset className={PARTY_CLASS} disabled={disabled}>
        <legend className={PARTY_LEGEND_CLASS}>{ct.tenant}</legend>
        <FormField
          label={ct.name}
          name="tenant_name"
          type="text"
          autoComplete="off"
          maxLength={CONTRACT_NAME_MAX}
          value={draft.tenant_name}
          error={error('tenant_name')}
          onChange={(event) => onChange({ tenant_name: event.target.value })}
        />
        <FormField
          label={ct.person_id}
          name="tenant_id"
          type="text"
          autoComplete="off"
          maxLength={CONTRACT_ID_MAX}
          value={draft.tenant_id}
          hint={ct.optional}
          error={error('tenant_id')}
          onChange={(event) => onChange({ tenant_id: event.target.value })}
        />
      </fieldset>

      <fieldset
        className="contract-form__terms m-0 flex min-w-0 flex-col gap-4 border-0 p-0"
        disabled={disabled}
      >
        <FormField
          label={ct.address}
          name="address"
          type="text"
          autoComplete="off"
          maxLength={CONTRACT_ADDRESS_MAX}
          value={draft.address}
          error={error('address')}
          onChange={(event) => onChange({ address: event.target.value })}
        />
        <FormField
          label={ct.start_date}
          name="start_date"
          type="date"
          value={draft.start_date}
          error={error('start_date')}
          onChange={(event) => onChange({ start_date: event.target.value })}
        />

        <PillGroup
          legend={ct.term}
          legendClassName={FORM_LEGEND_CLASS}
          options={CONTRACT_MONTHS_PRESETS.map((value) => ({
            value,
            label: fill(ct.months_pill, value),
          }))}
          selected={[months]}
          onToggle={(value) => onChange({ months: String(value) })}
        />
        <FormField
          label={ct.months}
          name="months"
          type="number"
          inputMode="numeric"
          min={1}
          max={CONTRACT_MONTHS_MAX}
          value={draft.months}
          error={error('months')}
          onChange={(event) => onChange({ months: event.target.value })}
        />

        <div className="contract-form__money grid grid-cols-2 gap-3">
          <FormField
            label={ct.rent}
            name="rent"
            type="number"
            inputMode="decimal"
            min={1}
            max={CONTRACT_MONEY_MAX}
            step="any"
            value={draft.rent}
            error={error('rent')}
            onChange={(event) => onChange({ rent: event.target.value })}
          />
          <SelectField
            label={ct.currency}
            name="currency"
            value={draft.currency}
            options={CONTRACT_CURRENCIES.map((code) => ({
              value: code,
              label: CURRENCY_LABELS[code],
            }))}
            onChange={(currency) => onChange({ currency: currency as Currency })}
          />
          <FormField
            label={ct.deposit}
            name="deposit"
            type="number"
            inputMode="decimal"
            min={0}
            max={CONTRACT_MONEY_MAX}
            step="any"
            value={contractDeposit(draft)}
            hint={ct.deposit_hint}
            error={error('deposit')}
            onChange={(event) => onChange({ deposit: event.target.value })}
          />
          <FormField
            label={ct.payment_day}
            name="payment_day"
            type="number"
            inputMode="numeric"
            min={1}
            max={CONTRACT_PAYMENT_DAY_MAX}
            value={draft.payment_day}
            hint={ct.payment_day_hint}
            error={error('payment_day')}
            onChange={(event) => onChange({ payment_day: event.target.value })}
          />
        </div>

        <PillGroup
          legend={ct.utilities}
          legendClassName={FORM_LEGEND_CLASS}
          options={CONTRACT_UTILITIES.map((value) => ({
            value,
            label: ct.utilities_options[value],
          }))}
          selected={[draft.utilities]}
          onToggle={(utilities) => onChange({ utilities })}
        />

        <div className="contract-form__pets overflow-hidden rounded-[var(--radius-md)] border border-[var(--border)]">
          <Switch
            label={ct.pets}
            checked={draft.pets_allowed}
            onChange={(pets_allowed) => onChange({ pets_allowed })}
          />
        </div>

        <TextAreaField
          label={ct.notes}
          name="notes"
          maxLength={CONTRACT_NOTES_MAX}
          value={draft.notes}
          placeholder={ct.notes_placeholder}
          hint={ct.optional}
          error={error('notes')}
          onChange={(event) => onChange({ notes: event.target.value })}
        />

        <PillGroup
          legend={ct.second_language}
          legendClassName={FORM_LEGEND_CLASS}
          options={CONTRACT_LANGUAGES.map((value) => ({ value, label: ct.languages[value] }))}
          selected={[draft.second_language]}
          onToggle={(second_language) => onChange({ second_language })}
        />
        <p className="contract-form__language-hint -mt-2 text-xs text-[var(--text-secondary)]">
          {ct.second_language_hint}
        </p>
      </fieldset>

      <p className="contract-form__disclaimer m-0 rounded-[var(--radius-md)] bg-[var(--surface-hover)] p-3 text-xs leading-relaxed text-[var(--text-secondary)]">
        {ct.disclaimer}
      </p>
    </form>
  );
}
