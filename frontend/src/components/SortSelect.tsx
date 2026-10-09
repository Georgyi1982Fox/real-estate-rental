import { useId } from 'react';
import { SORT_ORDERS, type SortOrder } from '../lib/searchFilters';
import { useI18n } from '../providers/I18nProvider';
import WheelPicker from './WheelPicker';

interface SortSelectProps {
  /** Сортировка из адреса; undefined — порядок сервера по умолчанию */
  value: SortOrder | undefined;
  /** Идёт поиск по словам: без сортировки сервер ставит сверху самые подходящие */
  byRelevance: boolean;
  onChange: (next: SortOrder | undefined) => void;
}

/** Порядок сервера без параметра sort, когда текста поиска нет */
const DEFAULT_ORDER: SortOrder = 'newest';
const RELEVANCE = 'relevance' as const;

/** Ярлык «Დალაგება» и барабан-пикер (WheelPicker) над результатами вместо выпадающего списка */
export default function SortSelect({ value, byRelevance, onChange }: SortSelectProps) {
  const { t } = useI18n();
  const st = t.home.sort;
  const labelId = useId();
  const options = byRelevance ? [RELEVANCE, ...SORT_ORDERS] : SORT_ORDERS;
  const selected = value ?? (byRelevance ? RELEVANCE : DEFAULT_ORDER);

  return (
    <div className="sort-select flex max-w-full items-center gap-2 text-sm text-[var(--text-secondary)]">
      <span id={labelId} className="sort-select__label shrink-0 font-bold">
        {st.label}
      </span>
      <WheelPicker
        aria-labelledby={labelId}
        className="w-44 sm:w-48"
        options={options.map((option) => ({ value: option, label: st[option] }))}
        value={selected}
        onChange={(next) => {
          // Выбор «по соответствию» — то же самое, что отсутствие параметра sort
          if (next === RELEVANCE) {
            onChange(undefined);
            return;
          }
          onChange(next === DEFAULT_ORDER && !byRelevance ? undefined : next);
        }}
      />
    </div>
  );
}
