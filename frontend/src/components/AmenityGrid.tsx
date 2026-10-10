import Icon, { type IconName } from './Icon';

export interface Amenity {
  code: string;
  name: string;
  icon: IconName;
}

interface AmenityGridProps {
  title: string;
  items: Amenity[];
}

/** Сетка удобств: иконка + подпись на языке интерфейса. Пустой список — блока нет */
export default function AmenityGrid({ title, items }: AmenityGridProps) {
  if (items.length === 0) return null;

  return (
    <>
      <h3 className="pt-2 text-sm font-semibold text-[var(--text-secondary)]">{title}</h3>
      <ul className="listing-amenities grid list-none grid-cols-2 gap-3 p-0 sm:grid-cols-3">
        {items.map(({ code, name, icon }) => (
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
