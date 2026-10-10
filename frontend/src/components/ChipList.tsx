import { fill } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import type { IconName } from './Icon';

/** Чип выбранного фильтра; patch убирает этот фильтр (нужные поля — undefined) */
export interface Chip<Patch> {
  key: string;
  label: string;
  patch: Patch;
  icon?: IconName;
}

interface ChipListProps<Patch> {
  chips: Chip<Patch>[];
  /** Убрать фильтр: в patch нужные поля равны undefined */
  onRemove: (patch: Patch) => void;
  /** Нажали на название чипа — открыть окно фильтров */
  onEdit: () => void;
}

/**
 * Чипы выбранных фильтров под строкой поиска. Убирает фильтр только крестик;
 * название открывает окно фильтров. Нет чипов — списка нет
 */
export default function ChipList<Patch>({ chips, onRemove, onEdit }: ChipListProps<Patch>) {
  const { t } = useI18n();
  const ht = t.home;

  if (chips.length === 0) return null;

  return (
    <ul className="filter-chips flex flex-wrap gap-2" aria-label={ht.active_filters}>
      {chips.map((chip) => (
        <li
          key={chip.key}
          className="filter-chips__chip inline-flex min-w-0 max-w-full items-center rounded-full bg-[var(--surface-hover)] text-sm font-medium text-[var(--text-primary)]"
        >
          <button
            type="button"
            className="filter-chips__label inline-flex min-h-9 min-w-0 items-center gap-1.5 rounded-full py-1.5 pl-3.5 pr-1 underline-offset-2 hover:underline"
            aria-haspopup="dialog"
            aria-label={fill(ht.edit_filter, chip.label)}
            onClick={() => {
              haptic('light');
              onEdit();
            }}
          >
            {chip.icon && <Icon name={chip.icon} className="size-4 text-[var(--text-secondary)]" />}
            <span className="truncate">{chip.label}</span>
          </button>
          {/* Крестик — отдельная кнопка; after расширяет зону нажатия до 44 px */}
          <button
            type="button"
            className="filter-chips__remove relative grid size-9 shrink-0 place-items-center rounded-full text-[var(--text-secondary)] transition-colors duration-200 after:absolute after:-inset-1 after:content-[''] hover:bg-[var(--border)] hover:text-[var(--text-primary)] active:scale-[.95]"
            aria-label={fill(ht.remove_filter, chip.label)}
            onClick={() => {
              haptic('light');
              onRemove(chip.patch);
            }}
          >
            <Icon name="close" className="size-4" />
          </button>
        </li>
      ))}
    </ul>
  );
}
