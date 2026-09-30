import { useCallback, useEffect, useState } from 'react';
import type { District, ListingsPage, SearchFilters } from '../api/types';
import { useApi } from '../hooks/useApi';
import { plural } from '../lib/format';
import { filtersToQuery, hasFilters } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import FilterPanel from './FilterPanel';
import Modal from './Modal';

/** Пауза после изменения фильтра перед подсчётом квартир */
const COUNT_DELAY_MS = 400;

const BUTTON_CLASS =
  'inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] px-4 py-2.5 text-sm font-semibold transition-colors duration-200 active:scale-[.98]';

interface FilterModalProps {
  open: boolean;
  onClose: () => void;
  /** Применённые фильтры (из адреса) — с них начинается правка в окне */
  filters: SearchFilters;
  districts: District[];
  /** «Показать»: новые фильтры целиком */
  onApply: (filters: SearchFilters) => void;
}

/**
 * Окно фильтров. Правки живут только в окне и применяются кнопкой «Показать N квартир»;
 * закрытие любым способом (✕, фон, Esc, свайп, «Назад») ничего не меняет.
 */
export default function FilterModal({
  open,
  onClose,
  filters,
  districts,
  onApply,
}: FilterModalProps) {
  const { lang, t } = useI18n();
  const ht = t.home;
  const [draft, setDraft] = useState<SearchFilters>(filters);
  const [wasOpen, setWasOpen] = useState(open);
  // Запрос, для которого считаем квартиры; null — окно закрыто
  const [countQuery, setCountQuery] = useState<string | null>(null);

  // Каждое открытие начинается с применённых фильтров
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) setDraft(filters);
    else setCountQuery(null);
  }

  const draftQuery = filtersToQuery(draft);

  // Считаем квартиры не на каждое нажатие, а после паузы; при открытии — сразу
  useEffect(() => {
    if (!open || draftQuery === countQuery) return;
    const timer = window.setTimeout(
      () => setCountQuery(draftQuery),
      countQuery === null ? 0 : COUNT_DELAY_MS,
    );
    return () => window.clearTimeout(timer);
  }, [open, draftQuery, countQuery]);

  const { data, error } = useApi<ListingsPage>(
    countQuery === null ? null : `/api/listings?per_page=1${countQuery ? `&${countQuery}` : ''}`,
  );
  const counting = countQuery !== draftQuery || (!data && !error);
  const total = counting ? undefined : data?.total;

  const change = useCallback((patch: SearchFilters) => {
    setDraft((current) => ({ ...current, ...patch }));
  }, []);

  const apply = () => {
    haptic('medium');
    onApply(draft);
    onClose();
  };

  let showLabel = ht.show_any;
  if (counting) showLabel = ht.show_loading;
  else if (total === 0) showLabel = ht.nothing_found;
  else if (total !== undefined) showLabel = plural(ht.show_count, total, lang);

  const footer = (
    <div className="filter-modal__actions flex gap-3">
      <button
        type="button"
        className={`${BUTTON_CLASS} text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] disabled:opacity-50 disabled:hover:bg-transparent`}
        disabled={!hasFilters(draft)}
        onClick={() => {
          haptic('light');
          setDraft({});
        }}
      >
        {ht.reset}
      </button>
      <button
        type="button"
        className={`${BUTTON_CLASS} flex-1 bg-[var(--primary)] text-white shadow-[var(--shadow-sm)] hover:bg-[var(--primary-hover)] disabled:bg-[var(--border)] disabled:text-[var(--text-secondary)] disabled:shadow-none`}
        disabled={total === 0}
        aria-busy={counting}
        aria-live="polite"
        onClick={apply}
      >
        {showLabel}
      </button>
    </div>
  );

  return (
    <Modal open={open} title={ht.filters} onClose={onClose} footer={footer}>
      <FilterPanel districts={districts} filters={draft} onChange={change} />
    </Modal>
  );
}
