import { useCityField } from '../hooks/useCityField';
import { HOTEL_ADDRESS_MAX } from '../lib/hotelForm';
import { useI18n } from '../providers/I18nProvider';
import FormField from './FormField';
import type { HotelFormStepProps } from './HotelFormMain';
import HotelPointField from './HotelPointField';
import SelectField from './SelectField';

/** Шаг 2 формы размещения: город, адрес и точка на карте */
export default function HotelFormPlace({ draft, onChange }: HotelFormStepProps) {
  const { t } = useI18n();
  const ft = t.hotel_form;
  const { options, center } = useCityField(draft.city);

  return (
    <>
      <SelectField
        label={ft.city}
        name="city"
        value={draft.city}
        options={options}
        placeholder={draft.city ? undefined : '—'}
        // Точка осталась бы в прежнем городе
        onChange={(code) => onChange({ city: code, latitude: null, longitude: null })}
      />
      <FormField
        label={ft.address}
        name="address"
        type="text"
        autoComplete="street-address"
        maxLength={HOTEL_ADDRESS_MAX}
        value={draft.address}
        onChange={(event) => onChange({ address: event.target.value })}
      />
      <HotelPointField
        latitude={draft.latitude}
        longitude={draft.longitude}
        center={center}
        onChange={(point) =>
          onChange({ latitude: point?.latitude ?? null, longitude: point?.longitude ?? null })
        }
      />
    </>
  );
}
