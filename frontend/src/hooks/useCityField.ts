import { tr } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import { DEFAULT_CITY, useCity } from './useCity';

/** Центр Тбилиси — пока список городов не загрузился или у города нет координат */
const FALLBACK_CENTER: [number, number] = [41.7151, 44.8271];

/** Поле «Город» в формах размещения: варианты выбора и центр карты для выбранного города */
export function useCityField(code: string) {
  const { lang, t } = useI18n();
  const { cities } = useCity();
  const options = cities.map((city) => ({ value: city.code, label: tr(city.name, lang) }));
  // Города может не быть в списке (в нём ещё нет квартир) — показываем его кодом
  if (code && !options.some((option) => option.value === code)) {
    options.unshift({ value: code, label: code === DEFAULT_CITY ? t.city.default_name : code });
  }
  const city = cities.find((item) => item.code === code);
  const center: [number, number] =
    typeof city?.latitude === 'number' && typeof city.longitude === 'number'
      ? [city.latitude, city.longitude]
      : FALLBACK_CENTER;

  return { options, center };
}
