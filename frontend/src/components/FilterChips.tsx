import type { SearchFilters } from '../api/types';
import type { DistrictNames } from '../hooks/useDistricts';
import { fill } from '../lib/format';
import {
  districtsLabel,
  extraFilterChips,
  filterDistricts,
  filterLabels,
  type FilterChip,
} from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

interface FilterChipsProps {
  filters: SearchFilters;
  districtNames: DistrictNames;
  /** Убрать фильтр: в patch нужные поля равны undefined */
  onRemove: (patch: SearchFilters) => void;
  /** Нажали на название чипа — открыть окно фильтров */
  onEdit: () => void;
}

/**
 * Чипы выбранных фильтров под строкой поиска: «Ваке, Сабуртало», «до 2 000 ₾», «2 комн.»,
 * затем дополнительные — «Не последний этаж», «Кондиционер», «Только собственник».
 * Убирает фильтр только крестик; название открывает окно фильтров.
 */
export default function FilterChips({
  filters,
  districtNames,
  onRemove,
  onEdit,
}: FilterChipsProps) {
  const { lang, t } = useI18n();
  const ht = t.home;
  const ids = filterDistricts(filters);
  // Пока названия районов грузятся — хотя бы их число
  const districts =
    districtsLabel(ids, districtNames, lang) ||
    (ids.length > 0 ? `${ht.districts}: ${ids.length}` : '');
  const labels = filterLabels(filters, districts, t.searches);

  const chips: FilterChip[] = [];
  if (labels.districts) {
    chips.push({
      key: 'districts',
      label: labels.districts,
      patch: { district: undefined, districts: undefined },
    });
  }
  if (labels.price) {
    chips.push({
      key: 'price',
      label: labels.price,
      patch: { min_price: undefined, max_price: undefined },
    });
  }
  if (labels.rooms) {
    chips.push({ key: 'rooms', label: labels.rooms, patch: { rooms: undefined } });
  }
  chips.push(...extraFilterChips(filters, t, lang));

  if (chips.length === 0) return null;

  return (
    <ul className="filter-chips flex flex-wrap gap-2" aria-label={ht.active_filters}>
      {chips.map((chip) => (
        <li
          key={chip.key}
          className="filter-chips__chip inline-flex min-w-0 max-w-full items-center rounded-full bg-[var(--surface-hover)] text-sm font-medium text-[var(--text-primary)]"
        >
          <button
            type="button"
            className="filter-chips__label inline-flex min-h-9 min-w-0 items-center gap-1.5 rounded-full py-1.5 pl-3.5 pr-1 underline-offset-2 hover:underline"
            aria-haspopup="dialog"
            aria-label={fill(ht.edit_filter, chip.label)}
            onClick={() => {
              haptic('light');
              onEdit();
            }}
          >
            {chip.key === 'districts' && (
              <Icon name="pin" className="size-4 text-[var(--text-secondary)]" />
            )}
            <span className="truncate">{chip.label}</span>
          </button>
          {/* Крестик — отдельная кнопка; after расширяет зону нажатия до 44 px */}
          <button
            type="button"
            className="filter-chips__remove relative grid size-9 shrink-0 place-items-center rounded-full text-[var(--text-secondary)] transition-colors duration-200 after:absolute after:-inset-1 after:content-[''] hover:bg-[var(--border)] hover:text-[var(--text-primary)] active:scale-[.95]"
            aria-label={fill(ht.remove_filter, chip.label)}
            onClick={() => {
              haptic('light');
              onRemove(chip.patch);
            }}
          >
            <Icon name="close" className="size-4" />
          </button>
        </li>
      ))}
    </ul>
  );
}
