import type { ListingId } from '../api/types';
import { useCompare } from '../hooks/useCompare';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

interface CompareButtonProps {
  listingId: ListingId;
}

/**
 * «⚖ Сравнить» на карточке: отмечает квартиру для сравнения (до 3). Лежит над
 * «растянутой» ссылкой карточки (z-10), поэтому нажатие квартиру не открывает
 */
export default function CompareButton({ listingId }: CompareButtonProps) {
  const { t } = useI18n();
  const ct = t.compare;
  const { has, toggle } = useCompare();
  const selected = has(listingId);

  return (
    <button
      type="button"
      className={`compare-button relative z-10 inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition-colors duration-200 after:absolute after:-inset-1 after:content-[''] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] active:scale-[.97] ${
        selected
          ? 'compare-button--on border-transparent bg-[var(--success-bg)] text-[var(--success-text)]'
          : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]'
      }`}
      aria-pressed={selected}
      aria-label={ct.button_label}
      onClick={() => toggle(listingId)}
    >
      <Icon name={selected ? 'check' : 'scale'} className="size-4" />
      <span aria-hidden="true">{selected ? ct.button_on : ct.button}</span>
    </button>
  );
}
