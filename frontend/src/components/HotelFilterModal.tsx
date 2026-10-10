import { useCallback, useState } from 'react';
import type { HotelFilters } from '../api/types';
import { useResultCount } from '../hooks/useResultCount';
import { plural } from '../lib/format';
import { hasHotelFilters, hotelsQuery } from '../lib/hotelFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import HotelFilterPanel from './HotelFilterPanel';
import Modal from './Modal';

const BUTTON_CLASS =
  'inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] px-4 py-2.5 text-sm font-semibold transition-colors duration-200 active:scale-[.98]';

interface HotelFilterModalProps {
  open: boolean;
  onClose: () => void;
  /** Применённые фильтры (из адреса) — с них начинается правка в окне */
  filters: HotelFilters;
  /** Выбранный город: окно его не меняет, но объекты считаются в нём */
  city: string | undefined;
  /** «Показать»: новые фильтры целиком */
  onApply: (filters: HotelFilters) => void;
}

/**
 * Окно фильтров гостиниц. Правки живут только в окне и применяются кнопкой
 * «Показать N объектов»; закрытие любым способом ничего не меняет
 */
export default function HotelFilterModal({
  open,
  onClose,
  filters,
  city,
  onApply,
}: HotelFilterModalProps) {
  const { lang, t } = useI18n();
  const ht = t.home;
  const [draft, setDraft] = useState<HotelFilters>(filters);
  const [wasOpen, setWasOpen] = useState(open);

  // Каждое открытие начинается с применённых фильтров
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) setDraft(filters);
  }

  const { counting, total } = useResultCount(
    open,
    hotelsQuery(draft, city),
    (query) => `/api/hotels?per_page=1${query ? `&${query}` : ''}`,
  );

  const change = useCallback((patch: HotelFilters) => {
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
  else if (total !== undefined) showLabel = plural(t.hotels.show_count, total, lang);

  const footer = (
    <div className="filter-modal__actions flex gap-3">
      <button
        type="button"
        className={`${BUTTON_CLASS} text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] disabled:opacity-50 disabled:hover:bg-transparent`}
        disabled={!hasHotelFilters(draft)}
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
      <HotelFilterPanel filters={draft} onChange={change} />
    </Modal>
  );
}
