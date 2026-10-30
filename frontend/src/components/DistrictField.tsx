import { useCityDistricts } from '../hooks/useDistricts';
import { tr } from '../lib/format';
import { LISTING_DISTRICT_MAX } from '../lib/ownerListings';
import { suggestDistricts } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import FormField from './FormField';
import { pillClass } from './PillGroup';

interface DistrictFieldProps {
  city: string;
  value: string;
  onChange: (district: string) => void;
}

/** Район текстом: сервер принимает любое название, подсказки — районы города (GET /api/districts) */
export default function DistrictField({ city, value, onChange }: DistrictFieldProps) {
  const { lang, t } = useI18n();
  const ft = t.listing_form;
  const districts = useCityDistricts(city || undefined);
  const typed = value.trim().toLocaleLowerCase();
  const suggestions = suggestDistricts(districts, value, lang, [])
    .map((district) => tr(district.name, lang))
    // Район уже выбран целиком — подсказывать нечего
    .filter((name) => name.toLocaleLowerCase() !== typed);

  return (
    <div className="district-field flex min-w-0 flex-col gap-2">
      <FormField
        label={ft.district}
        hint={ft.district_hint}
        name="district"
        type="text"
        autoComplete="off"
        maxLength={LISTING_DISTRICT_MAX}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      {suggestions.length > 0 && (
        <ul className="m-0 flex list-none flex-wrap gap-2 p-0" aria-label={ft.district_suggestions}>
          {suggestions.map((name) => (
            <li key={name}>
              <button
                type="button"
                className={pillClass(false)}
                onClick={() => {
                  haptic('selection');
                  onChange(name);
                }}
              >
                {name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
