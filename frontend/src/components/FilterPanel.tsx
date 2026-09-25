import type { District } from '../api/types';
import { tr } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

const PRICE_MIN = 100;
const PRICE_MAX = 2000;
const PRICE_STEP = 50;
const ROOM_OPTIONS = [
  { value: '1', label: '1' },
  { value: '2', label: '2' },
  { value: '3', label: '3' },
  { value: '4', label: '4+' },
];

const CONTROL_CLASS =
  'rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] text-sm text-[var(--text-primary)]';

interface FilterPanelProps {
  districts: District[];
}

/** Панель фильтров: район, цена, комнаты */
export default function FilterPanel({ districts }: FilterPanelProps) {
  const { lang, t } = useI18n();
  const ht = t.home;

  return (
    // Лёгкий отклик на смену любого фильтра (событие change всплывает до fieldset)
    <fieldset
      className="filter-panel flex flex-wrap gap-4 border-0 p-0"
      aria-label={ht.filters}
      onChange={() => haptic('selection')}
    >
      <legend className="sr-only">{ht.filters}</legend>

      <div className="filter-panel__field flex min-w-0 flex-col gap-1">
        <label htmlFor="filter-district" className="text-xs font-medium text-[var(--text-secondary)]">
          {ht.district}
        </label>
        <select id="filter-district" name="district" className={`${CONTROL_CLASS} px-3 py-2`}>
          <option value="">{ht.all_districts}</option>
          {districts.map((district) => (
            <option key={district.id} value={district.id}>
              {tr(district.name, lang)}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-panel__field flex min-w-0 flex-col gap-1">
        <span className="text-xs font-medium text-[var(--text-secondary)]" id="price-range-label">
          {ht.price}
        </span>
        <div className="flex items-center gap-2" role="group" aria-labelledby="price-range-label">
          <label className="sr-only" htmlFor="filter-price-min">
            {ht.price_min}
          </label>
          <input
            id="filter-price-min"
            name="min_price"
            type="number"
            inputMode="numeric"
            min={PRICE_MIN}
            max={PRICE_MAX}
            step={PRICE_STEP}
            defaultValue={PRICE_MIN}
            className={`${CONTROL_CLASS} w-20 px-2 py-2`}
          />
          <span className="text-[var(--text-secondary)]" aria-hidden="true">
            —
          </span>
          <label className="sr-only" htmlFor="filter-price-max">
            {ht.price_max}
          </label>
          <input
            id="filter-price-max"
            name="max_price"
            type="number"
            inputMode="numeric"
            min={PRICE_MIN}
            max={PRICE_MAX}
            step={PRICE_STEP}
            defaultValue={PRICE_MAX}
            className={`${CONTROL_CLASS} w-20 px-2 py-2`}
          />
        </div>
      </div>

      <div className="filter-panel__field flex min-w-0 flex-col gap-1">
        <label htmlFor="filter-rooms" className="text-xs font-medium text-[var(--text-secondary)]">
          {ht.rooms}
        </label>
        <select id="filter-rooms" name="rooms" className={`${CONTROL_CLASS} px-3 py-2`}>
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
