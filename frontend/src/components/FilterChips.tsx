import type { SearchFilters } from '../api/types';
import type { DistrictNames } from '../hooks/useDistricts';
import {
  districtsLabel,
  extraFilterChips,
  filterDistricts,
  filterLabels,
} from '../lib/searchFilters';
import { useI18n } from '../providers/I18nProvider';
import ChipList, { type Chip } from './ChipList';

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

  const chips: Chip<SearchFilters>[] = [];
  if (labels.districts) {
    chips.push({
      key: 'districts',
      label: labels.districts,
      icon: 'pin',
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

  return <ChipList chips={chips} onRemove={onRemove} onEdit={onEdit} />;
}
