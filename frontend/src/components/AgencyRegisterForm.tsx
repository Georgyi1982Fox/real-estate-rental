import { useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, apiPost } from '../api/client';
import type { AgencyCabinet } from '../api/types';
import {
  AGENCY_API,
  AGENCY_DESCRIPTION_MAX,
  AGENCY_FREE_LISTINGS,
  AGENCY_NAME_MAX,
  AGENCY_PHONE_MAX,
  agencyErrorText,
  cleanAgencyName,
  isAgencyName,
} from '../lib/agency';
import { fill } from '../lib/format';
import { compactPhone, isPhone } from '../lib/hotelForm';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import FormField from './FormField';
import Icon from './Icon';
import TextAreaField from './TextAreaField';

interface AgencyRegisterFormProps {
  onRegistered: (agency: AgencyCabinet) => void;
  /** Кабинет уже есть (открыт в другом окне или создан в боте) */
  onExists: () => void;
}

/** Регистрация риелтора: сразу, без одобрения. Телефон необязателен */
export default function AgencyRegisterForm({ onRegistered, onExists }: AgencyRegisterFormProps) {
  const { t } = useI18n();
  const at = t.agency;
  const showToast = useToast();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [phone, setPhone] = useState('');
  const [problems, setProblems] = useState({ name: false, phone: false });
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    const found = {
      name: !isAgencyName(name),
      phone: phone.trim() !== '' && !isPhone(phone),
    };
    setProblems(found);
    if (found.name || found.phone) return;
    setBusy(true);
    try {
      const agency = await apiPost<AgencyCabinet>(AGENCY_API, {
        name: cleanAgencyName(name),
        description: description.trim(),
        phone: compactPhone(phone) || null,
      });
      haptic('success');
      showToast(at.registered, 'success');
      onRegistered(agency);
    } catch (error) {
      haptic('error');
      showToast(agencyErrorText(error, at), 'error');
      if (error instanceof ApiError && error.status === 409) onExists();
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      className="agency-register flex flex-col gap-5"
      aria-labelledby="agency-register-title"
    >
      <header className="relative overflow-hidden rounded-[var(--radius-lg)] bg-linear-135 from-[var(--premium-from)] to-[var(--premium-to)] p-5 text-[var(--premium-ink)] shadow-[var(--shadow-md)]">
        <Icon
          name="briefcase"
          className="pointer-events-none absolute -right-3 -bottom-4 size-28 stroke-[1.2] opacity-20"
        />
        <h1 id="agency-register-title" className="relative text-xl font-bold tracking-tight">
          {at.invite_title}
        </h1>
        <p className="relative mt-1 text-sm font-medium leading-snug">
          {fill(at.invite_text, AGENCY_FREE_LISTINGS)}
        </p>
        <ul className="relative mt-3 flex list-none flex-col gap-1.5 p-0 text-sm">
          {at.benefits.map((benefit) => (
            <li key={benefit} className="flex items-start gap-2">
              <Icon name="check" className="mt-0.5 size-4 shrink-0" />
              <span>{benefit}</span>
            </li>
          ))}
        </ul>
      </header>

      <form className="flex flex-col gap-4" noValidate onSubmit={(event) => void submit(event)}>
        <FormField
          label={at.name}
          name="name"
          required
          autoComplete="organization"
          maxLength={AGENCY_NAME_MAX}
          hint={at.name_hint}
          error={problems.name ? at.errors.name : undefined}
          value={name}
          onChange={(event) => {
            setProblems((current) => ({ ...current, name: false }));
            setName(event.target.value);
          }}
        />
        <TextAreaField
          label={at.description}
          name="description"
          maxLength={AGENCY_DESCRIPTION_MAX}
          hint={at.optional}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
        <FormField
          label={at.phone}
          name="phone"
          type="tel"
          autoComplete="tel"
          maxLength={AGENCY_PHONE_MAX}
          hint={at.optional}
          error={problems.phone ? at.errors.phone : undefined}
          value={phone}
          onChange={(event) => {
            setProblems((current) => ({ ...current, phone: false }));
            setPhone(event.target.value);
          }}
        />
        <button
          type="submit"
          className="inline-flex min-h-12 items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-3 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98] disabled:opacity-60"
          disabled={busy}
          aria-busy={busy}
        >
          {busy && <span className="spinner" aria-hidden="true" />}
          {at.register}
        </button>
      </form>
    </section>
  );
}
