import { Link } from 'react-router-dom';
import { useFavorites } from '../hooks/useFavorites';
import { fill } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import LanguageSwitcher from './LanguageSwitcher';

export default function Header() {
  const { t } = useI18n();
  const { count } = useFavorites();

  return (
    // relative z-30: backdrop-blur создаёт свой stacking context — без z-index меню языка уходит под контент
    <header className="app-header relative z-30 border-b border-[var(--border)] bg-[var(--surface)]/90 pt-[var(--safe-top)] backdrop-blur-md">
      <nav
        className="mx-auto flex min-h-16 w-full max-w-screen-xl items-center justify-between gap-3 px-4 sm:px-6 lg:px-8"
        aria-label={t.header.nav}
      >
        <Link
          to="/"
          className="flex min-w-0 items-center gap-2 rounded-[var(--radius-md)]"
          aria-label={t.header.home}
        >
          <span className="grid size-10 shrink-0 place-items-center rounded-[var(--radius-md)] bg-[var(--primary)] text-sm font-bold text-white shadow-[var(--shadow-sm)]">
            B
          </span>
          <span className="truncate text-lg font-bold tracking-tight">Bina.ai</span>
        </Link>
        <div className="flex items-center gap-1">
          <LanguageSwitcher />
          <Link
            to="/favorites"
            className="app-icon-button app-header__favorites relative"
            aria-label={count > 0 ? fill(t.header.favorites_count, count) : t.header.favorites}
          >
            <span aria-hidden="true">♡</span>
            {count > 0 && (
              <span
                className="app-header__badge absolute -right-0.5 -top-0.5 inline-flex min-h-5 min-w-5 items-center justify-center rounded-full bg-[var(--danger)] px-1 text-[11px] font-bold leading-none text-white"
                aria-hidden="true"
              >
                {count > 99 ? '99+' : count}
              </span>
            )}
          </Link>
        </div>
      </nav>
    </header>
  );
}
