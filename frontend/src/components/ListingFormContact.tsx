import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import FormField from './FormField';
import type { ListingFormStepProps } from './ListingFormPlace';
import TelegramIcon from './TelegramIcon';

/** Шаг 4 размещения: телефон. С именем в Telegram он необязателен: напишут через бота */
export default function ListingFormContact({ draft, onChange }: ListingFormStepProps) {
  const { t } = useI18n();
  const ft = t.hotel_form;
  const { user } = useAuth();

  return (
    <>
      <FormField
        label={ft.phone}
        hint={ft.phone_hint}
        name="phone"
        type="tel"
        inputMode="tel"
        autoComplete="tel"
        maxLength={20}
        value={draft.phone}
        onChange={(event) => onChange({ phone: event.target.value })}
      />
      {user?.username && (
        <p className="m-0 flex items-start gap-2 rounded-[var(--radius-md)] bg-[var(--surface-hover)] px-3 py-2.5 text-sm text-[var(--text-secondary)]">
          <TelegramIcon className="mt-0.5 size-4" />
          <span className="min-w-0 break-words">{t.listing_form.telegram_note}</span>
        </p>
      )}
    </>
  );
}
