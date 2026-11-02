import { useState } from 'react';
import type { FormEvent } from 'react';
import { apiPatch } from '../api/client';
import type { AgencyCabinet } from '../api/types';
import {
  AGENCY_API,
  AGENCY_DESCRIPTION_MAX,
  AGENCY_NAME_MAX,
  agencyErrorText,
  cleanAgencyName,
  isAgencyName,
} from '../lib/agency';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import { DIALOG_BUTTON_CLASS, DIALOG_CANCEL_CLASS } from './ConfirmDialog';
import FormField from './FormField';
import Modal from './Modal';
import TextAreaField from './TextAreaField';

interface AgencyEditModalProps {
  agency: AgencyCabinet;
  open: boolean;
  onSaved: (agency: AgencyCabinet) => void;
  onClose: () => void;
}

/** Название и описание агентства (PATCH /api/agency) */
export default function AgencyEditModal({ agency, open, onSaved, onClose }: AgencyEditModalProps) {
  const { t } = useI18n();
  const at = t.agency;
  const showToast = useToast();
  const [wasOpen, setWasOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [invalid, setInvalid] = useState(false);
  const [busy, setBusy] = useState(false);

  // Каждое открытие — с текущих значений
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) {
      setName(agency.name);
      setDescription(agency.description);
      setInvalid(false);
    }
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    if (!isAgencyName(name)) {
      setInvalid(true);
      return;
    }
    setBusy(true);
    try {
      const saved = await apiPatch<AgencyCabinet>(AGENCY_API, {
        name: cleanAgencyName(name),
        description: description.trim(),
      });
      haptic('success');
      showToast(at.saved, 'success');
      onSaved(saved);
      onClose();
    } catch (error) {
      haptic('error');
      showToast(agencyErrorText(error, at), 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} title={at.edit} onClose={onClose}>
      <form className="flex flex-col gap-4" noValidate onSubmit={(event) => void submit(event)}>
        <FormField
          label={at.name}
          name="name"
          required
          maxLength={AGENCY_NAME_MAX}
          error={invalid ? at.errors.name : undefined}
          value={name}
          onChange={(event) => {
            setInvalid(false);
            setName(event.target.value);
          }}
        />
        <TextAreaField
          label={at.description}
          name="description"
          rows={5}
          maxLength={AGENCY_DESCRIPTION_MAX}
          hint={at.optional}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
        <footer className="mt-2 flex gap-3">
          <button type="button" className={DIALOG_CANCEL_CLASS} onClick={onClose}>
            {t.common.cancel}
          </button>
          <button
            type="submit"
            className={`${DIALOG_BUTTON_CLASS} bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)]`}
            disabled={busy}
            aria-busy={busy}
          >
            {t.hotel_form.save}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
