import type { SearchView } from '../hooks/useSearchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

const VIEWS: { view: SearchView; icon: 'list' | 'map' }[] = [
  { view: 'list', icon: 'list' },
  { view: 'map', icon: 'map' },
];

interface SearchViewToggleProps {
  value: SearchView;
  onChange: (view: SearchView) => void;
}

/** «☰ Список / 🗺 Карта» над результатами поиска (FRONTEND-056) */
export default function SearchViewToggle({ value, onChange }: SearchViewToggleProps) {
  const { t } = useI18n();
  const mt = t.home.map;

  return (
    <fieldset className="search-view inline-flex min-w-0 max-w-full shrink-0 rounded-full border border-[var(--border)] bg-[var(--surface)] p-1 shadow-[var(--shadow-sm)]">
      <legend className="sr-only">{mt.view_label}</legend>
      {VIEWS.map(({ view, icon }) => {
        const active = view === value;
        return (
          <button
            key={view}
            type="button"
            className={`search-view__option inline-flex min-h-9 min-w-0 items-center justify-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors duration-200 active:scale-[.98] ${
              active
                ? 'bg-[var(--primary)] text-white'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
            aria-pressed={active}
            onClick={() => {
              if (active) return;
              haptic('selection');
              onChange(view);
            }}
          >
            <Icon name={icon} className="size-4" />
            {view === 'map' ? mt.view_map : mt.view_list}
          </button>
        );
      })}
    </fieldset>
  );
}
