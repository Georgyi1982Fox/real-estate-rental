import { useCallback, useId, useMemo, useState } from 'react';
import type { District, SearchFilters } from '../api/types';
import { tr } from '../lib/format';
import { ROOMS_MAX, filterDistricts } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import PriceRange from './PriceRange';

/** С таким числом районов над списком появляется поиск */
const DISTRICT_SEARCH_FROM = 13;

const ROOM_OPTIONS = Array.from({ length: ROOMS_MAX }, (_, index) => index + 1);

const CONTROL_CLASS =
  'rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] text-sm text-[var(--text-primary)]';

const LEGEND_CLASS = 'mb-2 p-0 text-sm font-semibold text-[var(--text-primary)]';

/** Кнопка-«таблетка»: выбранная закрашена основным цветом */
function pillClass(selected: boolean): string {
  const state = selected
    ? 'border-[var(--primary)] bg-[var(--primary)] text-white'
    : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--surface-hover)]';
  return `filter-panel__pill inline-flex min-h-10 items-center justify-center rounded-full border px-3.5 py-2 text-sm font-medium transition-colors duration-200 active:scale-[.97] ${state}`;
}

interface FilterPanelProps {
  districts: District[];
  filters: SearchFilters;
  /** Изменить часть фильтров; undefined — убрать фильтр */
  onChange: (patch: SearchFilters) => void;
}

/** Поля фильтров для окна FilterModal: районы (несколько), цена, комнаты */
export default function FilterPanel({ districts, filters, onChange }: FilterPanelProps) {
  const { lang, t } = useI18n();
  const ht = t.home;
  const searchId = useId();
  const [query, setQuery] = useState('');
  const selected = filterDistricts(filters);

  // По алфавиту на языке интерфейса
  const sorted = useMemo(() => {
    const collator = new Intl.Collator(lang);
    return districts
      .map((district) => ({ id: district.id, name: tr(district.name, lang), all: district.name }))
      .sort((a, b) => collator.compare(a.name, b.name));
  }, [districts, lang]);

  // Ищем по названию на любом языке: «vake» найдёт «Ваке»
  const needle = query.trim().toLocaleLowerCase();
  const visible = needle
    ? sorted.filter((district) => {
        const names =
          typeof district.all === 'string' ? [district.all] : Object.values(district.all);
        return names.some((name) => name.toLocaleLowerCase().includes(needle));
      })
    : sorted;

  const toggleDistrict = (id: string) => {
    haptic('selection');
    const next = selected.includes(id) ? selected.filter((item) => item !== id) : [...selected, id];
    onChange({ district: undefined, districts: next.length > 0 ? next : undefined });
  };

  const toggleRooms = (rooms: number) => {
    haptic('selection');
    // Повторное нажатие снимает выбор
    onChange({ rooms: filters.rooms === rooms ? undefined : rooms });
  };

  const changePrice = useCallback(
    (min: number | undefined, max: number | undefined) => {
      onChange({ min_price: min, max_price: max });
    },
    [onChange],
  );

  return (
    <section className="filter-panel flex flex-col gap-6" aria-label={ht.filters}>
      <fieldset className="filter-panel__districts min-w-0 border-0 p-0">
        <legend className={LEGEND_CLASS}>{ht.districts}</legend>
        {districts.length >= DISTRICT_SEARCH_FROM && (
          <div className="relative mb-3">
            <label className="sr-only" htmlFor={searchId}>
              {ht.find_district}
            </label>
            <span
              className="pointer-events-none absolute inset-y-0 left-3 grid place-items-center text-[var(--text-secondary)]"
              aria-hidden="true"
            >
              <Icon name="search" className="size-4" />
            </span>
            <input
              id={searchId}
              type="search"
              value={query}
              placeholder={ht.find_district}
              autoComplete="off"
              className={`${CONTROL_CLASS} w-full py-2.5 pl-9 pr-3`}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
        )}
        {visible.length > 0 ? (
          <ul className="filter-panel__district-list flex flex-wrap gap-2">
            {visible.map((district) => {
              const active = selected.includes(district.id);
              return (
                <li key={district.id}>
                  <button
                    type="button"
                    className={pillClass(active)}
                    aria-pressed={active}
                    onClick={() => toggleDistrict(district.id)}
                  >
                    {district.name}
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="text-sm text-[var(--text-secondary)]">{ht.no_districts}</p>
        )}
      </fieldset>

      <PriceRange
        min={filters.min_price}
        max={filters.max_price}
        onChange={changePrice}
        inputClassName={CONTROL_CLASS}
        labelClassName={LEGEND_CLASS}
      />

      <fieldset className="filter-panel__rooms min-w-0 border-0 p-0">
        <legend className={LEGEND_CLASS}>{ht.rooms}</legend>
        <div className="flex flex-wrap gap-2">
          {ROOM_OPTIONS.map((rooms) => (
            <button
              key={rooms}
              type="button"
              className={`${pillClass(filters.rooms === rooms)} min-w-12`}
              aria-pressed={filters.rooms === rooms}
              onClick={() => toggleRooms(rooms)}
            >
              {rooms === 1 ? ht.room_studio : rooms === ROOMS_MAX ? `${rooms}+` : rooms}
            </button>
          ))}
        </div>
      </fieldset>
    </section>
  );
}
