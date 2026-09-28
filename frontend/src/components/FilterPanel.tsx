import { useCallback } from 'react';
import type { District, SearchFilters } from '../api/types';
import { tr } from '../lib/format';
import { ROOMS_MAX } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import PriceRange from './PriceRange';

const ROOM_OPTIONS = Array.from({ length: ROOMS_MAX }, (_, index) => {
  const rooms = index + 1;
  return { value: String(rooms), label: rooms === ROOMS_MAX ? `${rooms}+` : String(rooms) };
});

const CONTROL_CLASS =
  'rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] text-sm text-[var(--text-primary)]';

interface FilterPanelProps {
  districts: District[];
  filters: SearchFilters;
  /** Изменить часть фильтров; undefined — убрать фильтр */
  onChange: (patch: SearchFilters) => void;
}

/** Панель фильтров: район, цена, комнаты. Значения — из адреса страницы (useSearchFilters) */
export default function FilterPanel({ districts, filters, onChange }: FilterPanelProps) {
  const { lang, t } = useI18n();
  const ht = t.home;

  const changePrice = useCallback(
    (min: number | undefined, max: number | undefined) => {
      onChange({ min_price: min, max_price: max });
    },
    [onChange],
  );

  return (
    <fieldset className="filter-panel flex flex-wrap items-start gap-4 border-0 p-0">
      <legend className="sr-only">{ht.filters}</legend>

      <div className="filter-panel__field flex min-w-0 flex-col gap-1">
        <label
          htmlFor="filter-district"
          className="text-xs font-medium text-[var(--text-secondary)]"
        >
          {ht.district}
        </label>
        <select
          id="filter-district"
          name="district"
          className={`${CONTROL_CLASS} max-w-full px-3 py-2`}
          value={filters.district ?? ''}
          onChange={(event) => {
            haptic('selection');
            onChange({ district: event.target.value || undefined });
          }}
        >
          <option value="">{ht.all_districts}</option>
          {districts.map((district) => (
            <option key={district.id} value={district.id}>
              {tr(district.name, lang)}
            </option>
          ))}
        </select>
      </div>

      <PriceRange
        min={filters.min_price}
        max={filters.max_price}
        onChange={changePrice}
        inputClassName={CONTROL_CLASS}
      />

      <div className="filter-panel__field flex min-w-0 flex-col gap-1">
        <label htmlFor="filter-rooms" className="text-xs font-medium text-[var(--text-secondary)]">
          {ht.rooms}
        </label>
        <select
          id="filter-rooms"
          name="rooms"
          className={`${CONTROL_CLASS} px-3 py-2`}
          value={filters.rooms === undefined ? '' : String(filters.rooms)}
          onChange={(event) => {
            haptic('selection');
            const { value } = event.target;
            onChange({ rooms: value ? Number(value) : undefined });
          }}
        >
          <option value="">{ht.any}</option>
          {ROOM_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </fieldset>
  );
}
