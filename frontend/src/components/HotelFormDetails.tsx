import { useHotelOptions } from '../hooks/useHotelOptions';
import { hotelAmenityName } from '../i18n/hotels';
import { HOTEL_STARS_MAX } from '../lib/hotelFilters';
import { useI18n } from '../providers/I18nProvider';
import FormField from './FormField';
import { FORM_LEGEND_CLASS, type HotelFormStepProps } from './HotelFormMain';
import PillGroup from './PillGroup';

/** 0 — «Без звёзд» (гостевой дом, хостел) */
const NO_STARS = 0;

/** Шаг 3 формы размещения: звёзды, удобства, время заезда и выезда */
export default function HotelFormDetails({ draft, onChange }: HotelFormStepProps) {
  const { lang, t } = useI18n();
  const ht = t.hotels;
  const { amenities } = useHotelOptions();
  const starOptions = [
    { value: NO_STARS, label: t.hotel_form.no_stars },
    ...Array.from({ length: HOTEL_STARS_MAX }, (_, index) => ({
      value: index + 1,
      label: `${index + 1} ★`,
    })),
  ];

  const toggleAmenity = (code: string) => {
    const next = draft.amenities.includes(code)
      ? draft.amenities.filter((item) => item !== code)
      : [...draft.amenities, code];
    onChange({ amenities: next });
  };

  return (
    <>
      <PillGroup
        legend={ht.stars}
        legendClassName={FORM_LEGEND_CLASS}
        options={starOptions}
        selected={[draft.stars ?? NO_STARS]}
        onToggle={(value) => onChange({ stars: value === NO_STARS ? null : value })}
      />
      <PillGroup
        legend={ht.amenities}
        legendClassName={FORM_LEGEND_CLASS}
        options={amenities.map((code) => ({
          value: code,
          label: hotelAmenityName(code, lang) ?? code,
        }))}
        selected={draft.amenities}
        onToggle={toggleAmenity}
      />
      <div className="hotel-form__times grid grid-cols-2 gap-3">
        <FormField
          label={ht.check_in}
          name="check_in"
          type="time"
          value={draft.check_in}
          onChange={(event) => onChange({ check_in: event.target.value })}
        />
        <FormField
          label={ht.check_out}
          name="check_out"
          type="time"
          value={draft.check_out}
          onChange={(event) => onChange({ check_out: event.target.value })}
        />
      </div>
    </>
  );
}
