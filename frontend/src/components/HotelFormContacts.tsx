import { fill } from '../lib/format';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import FormField from './FormField';
import type { HotelFormStepProps } from './HotelFormMain';
import TelegramIcon from './TelegramIcon';

/**
 * Шаг 6 формы размещения: телефон и WhatsApp. Ссылку на Telegram сервер берёт сам —
 * из имени пользователя; без имени телефон обязателен
 */
export default function HotelFormContacts({ draft, onChange }: HotelFormStepProps) {
  const { t } = useI18n();
  const ft = t.hotel_form;
  const { user } = useAuth();
  const username = user?.username ?? '';

  return (
    <>
      <FormField
        label={ft.phone}
        hint={ft.phone_hint}
        name="phone"
        type="tel"
        inputMode="tel"
        autoComplete="tel"
        value={draft.phone}
        onChange={(event) => onChange({ phone: event.target.value })}
      />
      <FormField
        label={ft.whatsapp}
        name="whatsapp"
        type="tel"
        inputMode="tel"
        autoComplete="off"
        value={draft.whatsapp}
        onChange={(event) => onChange({ whatsapp: event.target.value })}
      />
      {username && (
        <p className="hotel-form__telegram m-0 flex items-start gap-2 rounded-[var(--radius-md)] bg-[var(--surface-hover)] px-3 py-2.5 text-sm text-[var(--text-secondary)]">
          <TelegramIcon className="mt-0.5 size-4" />
          <span className="min-w-0 break-words">{fill(ft.telegram_note, username)}</span>
        </p>
      )}
    </>
  );
}
