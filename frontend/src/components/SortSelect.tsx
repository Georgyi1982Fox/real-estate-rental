import { SORT_ORDERS, parseSort, type SortOrder } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

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

/** «Сортировка ▾» над результатами — системный список, на телефоне открывается родным окном */
export default function SortSelect({ value, byRelevance, onChange }: SortSelectProps) {
  const { t } = useI18n();
  const st = t.home.sort;
  const options = byRelevance ? [RELEVANCE, ...SORT_ORDERS] : SORT_ORDERS;
  const selected = value ?? (byRelevance ? RELEVANCE : DEFAULT_ORDER);

  return (
    <label className="sort-select inline-flex max-w-full items-center gap-2 text-sm text-[var(--text-secondary)]">
      <span className="sort-select__label shrink-0">{st.label}</span>
      <select
        className="sort-select__field min-h-11 min-w-0 max-w-full cursor-pointer rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm font-medium text-[var(--text-primary)] shadow-[var(--shadow-sm)] transition-colors duration-200 hover:bg-[var(--surface-hover)]"
        value={selected}
        onChange={(event) => {
          haptic('light');
          const next = parseSort(event.target.value);
          // Порядок по умолчанию в адресе не держим
          onChange(next === DEFAULT_ORDER && !byRelevance ? undefined : next);
        }}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {st[option]}
          </option>
        ))}
      </select>
    </label>
  );
}
