import { useCityField } from '../hooks/useCityField';
import { LISTING_ADDRESS_MAX, type ListingDraft } from '../lib/ownerListings';
import { useI18n } from '../providers/I18nProvider';
import DistrictField from './DistrictField';
import FormField from './FormField';
import HotelPointField from './HotelPointField';
import SelectField from './SelectField';

export interface ListingFormStepProps {
  draft: ListingDraft;
  /** Изменить часть черновика */
  onChange: (patch: Partial<ListingDraft>) => void;
}

/** Шаг 1 размещения: город, район и, по желанию, адрес и точка на карте */
export default function ListingFormPlace({ draft, onChange }: ListingFormStepProps) {
  const { t } = useI18n();
  const ft = t.listing_form;
  const { options, center } = useCityField(draft.city);

  return (
    <>
      <SelectField
        label={t.hotel_form.city}
        name="city"
        value={draft.city}
        options={options}
        placeholder={draft.city ? undefined : '—'}
        // Район и точка остались бы в прежнем городе
        onChange={(code) => onChange({ city: code, district: '', latitude: null, longitude: null })}
      />
      <DistrictField
        city={draft.city}
        value={draft.district}
        onChange={(district) => onChange({ district })}
      />
      <FormField
        label={ft.address}
        name="address"
        type="text"
        autoComplete="street-address"
        maxLength={LISTING_ADDRESS_MAX}
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
      <p className="m-0 text-xs text-[var(--text-secondary)]">{ft.point_note}</p>
    </>
  );
}
