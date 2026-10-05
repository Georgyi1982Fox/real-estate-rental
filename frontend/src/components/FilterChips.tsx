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
}

/**
 * Чипы выбранных фильтров под строкой поиска: «Ваке, Сабуртало», «до 2 000 ₾», «2 комн.»,
 * затем дополнительные — «Не последний этаж», «Кондиционер», «Только собственник»
 */
export default function FilterChips({ filters, districtNames, onRemove }: FilterChipsProps) {
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
        <li key={chip.key} className="min-w-0 max-w-full">
          <button
            type="button"
            className="filter-chips__chip inline-flex min-h-9 max-w-full items-center gap-1.5 rounded-full bg-[var(--surface-hover)] py-1.5 pl-3.5 pr-2.5 text-sm font-medium text-[var(--text-primary)] transition-colors duration-200 hover:bg-[var(--border)] active:scale-[.97]"
            aria-label={fill(ht.remove_filter, chip.label)}
            onClick={() => {
              haptic('light');
              onRemove(chip.patch);
            }}
          >
            <span className="truncate">{chip.label}</span>
            <Icon name="close" className="size-4 text-[var(--text-secondary)]" />
          </button>
        </li>
      ))}
    </ul>
  );
}
