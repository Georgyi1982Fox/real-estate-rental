import { useCallback, useId, useMemo, useState } from 'react';
import type { District, SearchFilters } from '../api/types';
import { CONDITION_CODES, conditionName } from '../i18n/conditions';
import { FEATURE_CODES, featureName } from '../i18n/features';
import { fill, tr } from '../lib/format';
import {
  AREA_MAX,
  BATHROOMS_MAX,
  BEDROOMS_MAX,
  FLOOR_MAX,
  ROOMS_MAX,
  countText,
  filterDistricts,
} from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import PillGroup, { pillClass } from './PillGroup';
import PriceRange from './PriceRange';
import RangeField from './RangeField';
import Switch from './Switch';

/** С таким числом районов над списком появляется поиск */
const DISTRICT_SEARCH_FROM = 13;
const AREA_STEP = 5;

const AREA_NAMES = { min: 'min_area', max: 'max_area' };
const FLOOR_NAMES = { min: 'floor_min', max: 'floor_max' };
const FLOOR_FLAGS = ['not_first_floor', 'not_last_floor'] as const;

/** Числа 1…max для таблеток; последнее значение — «и больше» */
const countOptions = (max: number) =>
  Array.from({ length: max }, (_, index) => ({
    value: index + 1,
    label: countText(index + 1, max),
  }));

const BEDROOM_OPTIONS = countOptions(BEDROOMS_MAX);
const BATHROOM_OPTIONS = countOptions(BATHROOMS_MAX);

const CONTROL_CLASS =
  'rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] text-sm text-[var(--text-primary)]';

const LEGEND_CLASS = 'mb-2 p-0 text-sm font-semibold text-[var(--text-primary)]';

interface FilterPanelProps {
  districts: District[];
  filters: SearchFilters;
  /** Изменить часть фильтров; undefined — убрать фильтр */
  onChange: (patch: SearchFilters) => void;
}

/**
 * Поля фильтров для окна FilterModal: районы (несколько), цена, комнаты, площадь, спальни,
 * санузлы, этаж, состояние, удобства, «только собственник»
 */
export default function FilterPanel({ districts, filters, onChange }: FilterPanelProps) {
  const { lang, t } = useI18n();
  const ht = t.home;
  const ft = t.filters;
  const searchId = useId();
  const [query, setQuery] = useState('');
  const selected = filterDistricts(filters);
  const features = filters.features ?? [];
  const conditions = filters.condition ?? [];

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

  const roomOptions = useMemo(
    () =>
      Array.from({ length: ROOMS_MAX }, (_, index) => ({
        value: index + 1,
        label: index === 0 ? ht.room_studio : countText(index + 1, ROOMS_MAX),
      })),
    [ht],
  );
  const conditionOptions = useMemo(
    () =>
      CONDITION_CODES.map((code) => ({ value: code, label: conditionName(code, lang) ?? code })),
    [lang],
  );
  const featureOptions = useMemo(
    () => FEATURE_CODES.map((code) => ({ value: code, label: featureName(code, lang) ?? code })),
    [lang],
  );

  const toggleDistrict = (id: string) => {
    haptic('selection');
    const next = selected.includes(id) ? selected.filter((item) => item !== id) : [...selected, id];
    onChange({ district: undefined, districts: next.length > 0 ? next : undefined });
  };

  /** Одно значение из группы; повторное нажатие снимает выбор */
  const toggleNumber = (key: 'rooms' | 'bedrooms' | 'bathrooms', value: number) => {
    onChange({ [key]: filters[key] === value ? undefined : value });
  };

  /** Несколько значений из группы; пустой список — фильтра нет */
  const toggleCode = (key: 'features' | 'condition', codes: string[], code: string) => {
    const next = codes.includes(code) ? codes.filter((item) => item !== code) : [...codes, code];
    onChange({ [key]: next.length > 0 ? next : undefined });
  };

  // Стабильные ссылки: RangeField перезапускает таймер ввода при смене onChange
  const changePrice = useCallback(
    (min: number | undefined, max: number | undefined) => {
      onChange({ min_price: min, max_price: max });
    },
    [onChange],
  );
  const changeArea = useCallback(
    (min: number | undefined, max: number | undefined) => {
      onChange({ min_area: min, max_area: max });
    },
    [onChange],
  );
  const changeFloor = useCallback(
    (min: number | undefined, max: number | undefined) => {
      onChange({ floor_min: min, floor_max: max });
    },
    [onChange],
  );

  const rangeErrors = (limit: number) => ({
    min: ft.range_min_error,
    max: ft.range_max_error,
    limit: fill(ft.range_limit_error, limit),
  });

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

      <PillGroup
        className="filter-panel__rooms"
        legend={ht.rooms}
        legendClassName={LEGEND_CLASS}
        options={roomOptions}
        selected={filters.rooms === undefined ? [] : [filters.rooms]}
        onToggle={(value) => toggleNumber('rooms', value)}
        compact
      />

      <RangeField
        label={ft.area}
        minLabel={ft.area_min}
        maxLabel={ft.area_max}
        names={AREA_NAMES}
        min={filters.min_area}
        max={filters.max_area}
        limit={AREA_MAX}
        step={AREA_STEP}
        errors={rangeErrors(AREA_MAX)}
        onChange={changeArea}
        inputClassName={CONTROL_CLASS}
        labelClassName={LEGEND_CLASS}
      />

      <PillGroup
        className="filter-panel__bedrooms"
        legend={ft.bedrooms}
        legendClassName={LEGEND_CLASS}
        options={BEDROOM_OPTIONS}
        selected={filters.bedrooms === undefined ? [] : [filters.bedrooms]}
        onToggle={(value) => toggleNumber('bedrooms', value)}
        compact
      />

      <PillGroup
        className="filter-panel__bathrooms"
        legend={ft.bathrooms}
        legendClassName={LEGEND_CLASS}
        options={BATHROOM_OPTIONS}
        selected={filters.bathrooms === undefined ? [] : [filters.bathrooms]}
        onToggle={(value) => toggleNumber('bathrooms', value)}
        compact
      />

      <div className="filter-panel__floor flex min-w-0 flex-col gap-3">
        <RangeField
          label={ft.floor}
          minLabel={ft.floor_min}
          maxLabel={ft.floor_max}
          names={FLOOR_NAMES}
          min={filters.floor_min}
          max={filters.floor_max}
          lowest={1}
          limit={FLOOR_MAX}
          errors={rangeErrors(FLOOR_MAX)}
          onChange={changeFloor}
          inputClassName={CONTROL_CLASS}
          labelClassName={LEGEND_CLASS}
        />
        <div className="flex flex-wrap gap-2">
          {FLOOR_FLAGS.map((key) => (
            <button
              key={key}
              type="button"
              className={pillClass(filters[key] === true)}
              aria-pressed={filters[key] === true}
              onClick={() => {
                haptic('selection');
                onChange({ [key]: filters[key] ? undefined : true });
              }}
            >
              {ft[key]}
            </button>
          ))}
        </div>
      </div>

      <PillGroup
        className="filter-panel__condition"
        legend={ft.condition}
        legendClassName={LEGEND_CLASS}
        options={conditionOptions}
        selected={conditions}
        onToggle={(code) => toggleCode('condition', conditions, code)}
      />

      <PillGroup
        className="filter-panel__features"
        legend={ft.features}
        legendClassName={LEGEND_CLASS}
        options={featureOptions}
        selected={features}
        onToggle={(code) => toggleCode('features', features, code)}
      />

      <div className={`filter-panel__owner overflow-hidden ${CONTROL_CLASS}`}>
        <Switch
          label={ft.owner_only}
          checked={filters.owner_only === true}
          onChange={(checked) => onChange({ owner_only: checked ? true : undefined })}
        />
      </div>
    </section>
  );
}
