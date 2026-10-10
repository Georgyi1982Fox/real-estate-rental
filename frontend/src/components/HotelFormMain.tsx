import { useHotelOptions } from '../hooks/useHotelOptions';
import { hotelKindName } from '../i18n/hotels';
import { HOTEL_NAME_MAX, type HotelDraft } from '../lib/hotelForm';
import { useI18n } from '../providers/I18nProvider';
import FormField from './FormField';
import PillGroup from './PillGroup';

export const FORM_LEGEND_CLASS = 'mb-2 p-0 text-sm font-medium text-[var(--text-primary)]';

export interface HotelFormStepProps {
  draft: HotelDraft;
  /** Изменить часть черновика */
  onChange: (patch: Partial<HotelDraft>) => void;
}

/** Шаг 1 формы размещения: тип объекта и название */
export default function HotelFormMain({ draft, onChange }: HotelFormStepProps) {
  const { lang, t } = useI18n();
  const { kinds } = useHotelOptions();

  return (
    <>
      <PillGroup
        legend={t.hotels.kind}
        legendClassName={FORM_LEGEND_CLASS}
        options={kinds.map((code) => ({ value: code, label: hotelKindName(code, lang) ?? code }))}
        selected={draft.kind ? [draft.kind] : []}
        onToggle={(kind) => onChange({ kind })}
      />
      <FormField
        label={t.hotel_form.name}
        name="name"
        type="text"
        autoComplete="off"
        maxLength={HOTEL_NAME_MAX}
        value={draft.name}
        onChange={(event) => onChange({ name: event.target.value })}
      />
    </>
  );
}
