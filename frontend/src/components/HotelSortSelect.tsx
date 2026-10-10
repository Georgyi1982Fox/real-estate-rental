import { useId } from 'react';
import { HOTEL_DEFAULT_SORT, HOTEL_SORTS, type HotelSort } from '../lib/hotelFilters';
import { useI18n } from '../providers/I18nProvider';
import WheelPicker from './WheelPicker';

interface HotelSortSelectProps {
  /** Сортировка из адреса; undefined — порядок сервера по умолчанию */
  value: HotelSort | undefined;
  onChange: (next: HotelSort | undefined) => void;
}

/** Сортировка гостиниц: тот же барабан, что у квартир (SortSelect), со своим набором порядков */
export default function HotelSortSelect({ value, onChange }: HotelSortSelectProps) {
  const { t } = useI18n();
  const st = t.home.sort;
  const labelId = useId();
  const labels: Record<HotelSort, string> = {
    newest: st.newest,
    price_asc: st.price_asc,
    price_desc: st.price_desc,
    stars_desc: t.hotels.sort_stars,
  };

  return (
    <div className="sort-select flex max-w-full items-center gap-2 text-sm text-[var(--text-secondary)]">
      <span id={labelId} className="sort-select__label shrink-0 font-bold">
        {st.label}
      </span>
      <WheelPicker
        aria-labelledby={labelId}
        className="w-44 sm:w-48"
        options={HOTEL_SORTS.map((option) => ({ value: option, label: labels[option] }))}
        value={value ?? HOTEL_DEFAULT_SORT}
        // Порядок по умолчанию в адресе не держим
        onChange={(next) => onChange(next === HOTEL_DEFAULT_SORT ? undefined : next)}
      />
    </div>
  );
}
