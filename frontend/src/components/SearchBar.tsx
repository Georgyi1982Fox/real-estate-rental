import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

/** Строка поиска по району, улице, комплексу */
export default function SearchBar() {
  const { t } = useI18n();
  const ht = t.home;

  return (
    <search className="search-bar flex flex-col gap-3 sm:flex-row" aria-label={ht.search_label}>
      <label className="sr-only" htmlFor="search-input">
        {ht.search_placeholder}
      </label>
      <div className="relative flex-1">
        <span
          className="pointer-events-none absolute inset-y-0 left-3 grid place-items-center text-[var(--text-secondary)]"
          aria-hidden="true"
        >
          🔍
        </span>
        <input
          id="search-input"
          type="search"
          name="q"
          placeholder={ht.search_placeholder}
          className="w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] py-3 pl-10 pr-4 text-sm text-[var(--text-primary)] shadow-[var(--shadow-sm)]"
        />
      </div>
      <button
        type="button"
        onClick={() => haptic('light')}
        className="inline-flex items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-3 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)]"
      >
        {ht.search_button}
      </button>
    </search>
  );
}
