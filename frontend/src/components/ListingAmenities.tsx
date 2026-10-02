import { featureName } from '../i18n/features';
import { useI18n } from '../providers/I18nProvider';
import Icon, { type IconName } from './Icon';

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
    return name ? [{ code, name, icon: FEATURE_ICONS[code] ?? 'check' }] : [];
  });

  if (features.length === 0) return null;

  return (
    <>
      <h3 className="pt-2 text-sm font-semibold text-[var(--text-secondary)]">
        {t.listing.amenities}
      </h3>
      <ul className="listing-amenities grid list-none grid-cols-2 gap-3 p-0 sm:grid-cols-3">
        {features.map(({ code, name, icon }) => (
          <li
            key={code}
            className="listing-amenities__item flex min-w-0 items-center gap-2 text-[13px] leading-snug sm:text-sm"
          >
            <span className="listing-amenities__icon inline-flex size-8 shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--surface-hover)] text-[var(--text-primary)]">
              <Icon name={icon} />
            </span>
            <span className="min-w-0 break-words">{name}</span>
          </li>
        ))}
      </ul>
    </>
  );
}
