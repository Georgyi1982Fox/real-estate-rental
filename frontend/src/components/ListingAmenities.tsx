import { featureName } from '../i18n/features';
import { useI18n } from '../providers/I18nProvider';
import AmenityGrid from './AmenityGrid';
import type { IconName } from './Icon';

interface ListingAmenitiesProps {
  /** Коды удобств с бэкенда; неизвестные не показываются */
  codes: string[];
}

// furnished — старый код из моков, показываем как мебель
const FEATURE_ICONS: Record<string, IconName> = {
  furniture: 'sofa',
  furnished: 'sofa',
  kitchen_appliances: 'pot',
  air_conditioning: 'snowflake',
  heating: 'thermometer',
  hot_water: 'droplet',
  washing_machine: 'washer',
  dishwasher: 'utensils',
  fridge: 'fridge',
  tv: 'tv',
  internet: 'wifi',
  gas: 'flame',
  elevator: 'elevator',
  parking: 'parking',
  balcony: 'balcony',
  storage: 'archive',
  pool: 'waves',
  pets_allowed: 'paw',
  security: 'shield',
};

/** Сетка удобств: иконка + подпись на языке интерфейса. Нет известных кодов — блока нет */
export default function ListingAmenities({ codes }: ListingAmenitiesProps) {
  const { lang, t } = useI18n();
  // Набор убирает повторы: сайт может прислать один код дважды
  const features = [...new Set(codes)].flatMap((code) => {
    const name = featureName(code, lang);
    const icon: IconName = FEATURE_ICONS[code] ?? 'check';
    return name ? [{ code, name, icon }] : [];
  });

  return <AmenityGrid title={t.listing.amenities} items={features} />;
}
