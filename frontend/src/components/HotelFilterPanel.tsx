import { useCallback, useMemo } from 'react';
import type { HotelFilters } from '../api/types';
import { useHotelOptions } from '../hooks/useHotelOptions';
import { hotelAmenityName, hotelKindName } from '../i18n/hotels';
import { fill, formatPrice } from '../lib/format';
import {
  HOTEL_GUESTS_MAX,
  HOTEL_PRICE_MAX,
  HOTEL_PRICE_STEP,
  HOTEL_STARS_MAX,
  guestsText,
  starsText,
} from '../lib/hotelFilters';
import { useI18n } from '../providers/I18nProvider';
import PillGroup from './PillGroup';
import RangeField from './RangeField';

const PRICE_NAMES = { min: 'price_min', max: 'price_max' };

const GUEST_OPTIONS = Array.from({ length: HOTEL_GUESTS_MAX }, (_, index) => ({
  value: index + 1,
  label: guestsText(index + 1),
}));

const CONTROL_CLASS =
  'rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] text-sm text-[var(--text-primary)]';
const LEGEND_CLASS = 'mb-2 p-0 text-sm font-semibold text-[var(--text-primary)]';

interface HotelFilterPanelProps {
  filters: HotelFilters;
  /** Изменить часть фильтров; undefined — убрать фильтр */
  onChange: (patch: HotelFilters) => void;
}

/** Поля фильтров гостиниц для окна HotelFilterModal: тип, гости, цена за ночь, звёзды, удобства */
export default function HotelFilterPanel({ filters, onChange }: HotelFilterPanelProps) {
  const { lang, t } = useI18n();
  const ht = t.hotels;
  const { kinds, amenities } = useHotelOptions();
  const selectedKinds = filters.kind ?? [];
  const selectedAmenities = filters.amenities ?? [];

  const kindOptions = useMemo(
    () => kinds.map((code) => ({ value: code, label: hotelKindName(code, lang) ?? code })),
    [kinds, lang],
  );
  const starOptions = useMemo(
    () =>
      Array.from({ length: HOTEL_STARS_MAX }, (_, index) => ({
        value: index + 1,
        label: starsText(index + 1, t.searches),
      })),
    [t],
  );
  const amenityOptions = useMemo(
    () => amenities.map((code) => ({ value: code, label: hotelAmenityName(code, lang) ?? code })),
    [amenities, lang],
  );

  /** Несколько значений из группы; пустой список — фильтра нет */
  const toggleCode = (key: 'kind' | 'amenities', codes: string[], code: string) => {
    const next = codes.includes(code) ? codes.filter((item) => item !== code) : [...codes, code];
    onChange({ [key]: next.length > 0 ? next : undefined });
  };

  /** Одно значение из группы; повторное нажатие снимает выбор */
  const toggleNumber = (key: 'guests' | 'stars', value: number) => {
    onChange({ [key]: filters[key] === value ? undefined : value });
  };

  // Стабильная ссылка: RangeField перезапускает таймер ввода при смене onChange
  const changePrice = useCallback(
    (min: number | undefined, max: number | undefined) => {
      onChange({ price_min: min, price_max: max });
    },
    [onChange],
  );

  return (
    <section className="filter-panel flex flex-col gap-6" aria-label={t.home.filters}>
      <PillGroup
        className="filter-panel__kind"
        legend={ht.kind}
        legendClassName={LEGEND_CLASS}
        options={kindOptions}
        selected={selectedKinds}
        onToggle={(code) => toggleCode('kind', selectedKinds, code)}
      />

      <PillGroup
        className="filter-panel__guests"
        legend={ht.guests}
        legendClassName={LEGEND_CLASS}
        options={GUEST_OPTIONS}
        selected={filters.guests === undefined ? [] : [filters.guests]}
        onToggle={(value) => toggleNumber('guests', value)}
        compact
      />

      <RangeField
        label={ht.price}
        minLabel={t.home.price_min}
        maxLabel={t.home.price_max}
        names={PRICE_NAMES}
        min={filters.price_min}
        max={filters.price_max}
        limit={HOTEL_PRICE_MAX}
        step={HOTEL_PRICE_STEP}
        errors={{
          min: t.home.price_min_error,
          max: t.home.price_max_error,
          limit: fill(t.home.price_limit_error, formatPrice(HOTEL_PRICE_MAX)),
        }}
        onChange={changePrice}
        inputClassName={CONTROL_CLASS}
        labelClassName={LEGEND_CLASS}
      />

      <PillGroup
        className="filter-panel__stars"
        legend={ht.stars}
        legendClassName={LEGEND_CLASS}
        options={starOptions}
        selected={filters.stars === undefined ? [] : [filters.stars]}
        onToggle={(value) => toggleNumber('stars', value)}
        compact
      />

      <PillGroup
        className="filter-panel__amenities"
        legend={ht.amenities}
        legendClassName={LEGEND_CLASS}
        options={amenityOptions}
        selected={selectedAmenities}
        onToggle={(code) => toggleCode('amenities', selectedAmenities, code)}
      />
    </section>
  );
}
