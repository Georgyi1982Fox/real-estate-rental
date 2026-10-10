import { DEFAULT_CITY, useCity } from '../hooks/useCity';
import { tr } from '../lib/format';
import { HOTEL_ADDRESS_MAX } from '../lib/hotelForm';
import { useI18n } from '../providers/I18nProvider';
import FormField from './FormField';
import type { HotelFormStepProps } from './HotelFormMain';
import HotelPointField from './HotelPointField';
import SelectField from './SelectField';

/** Центр Тбилиси — пока список городов не загрузился или у города нет координат */
const FALLBACK_CENTER: [number, number] = [41.7151, 44.8271];

/** Шаг 2 формы размещения: город, адрес и точка на карте */
export default function HotelFormPlace({ draft, onChange }: HotelFormStepProps) {
  const { lang, t } = useI18n();
  const ft = t.hotel_form;
  const { cities } = useCity();
  const options = cities.map((city) => ({ value: city.code, label: tr(city.name, lang) }));
  // Город объекта может не быть в списке (в нём ещё нет квартир) — показываем его кодом
  if (draft.city && !options.some((option) => option.value === draft.city)) {
    options.unshift({
      value: draft.city,
      label: draft.city === DEFAULT_CITY ? t.city.default_name : draft.city,
    });
  }
  const city = cities.find((item) => item.code === draft.city);
  const center: [number, number] =
    typeof city?.latitude === 'number' && typeof city.longitude === 'number'
      ? [city.latitude, city.longitude]
      : FALLBACK_CENTER;

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
