import { Link } from 'react-router-dom';
import { useI18n } from '../providers/I18nProvider';
import LanguageSwitcher from './LanguageSwitcher';

export default function Header() {
  const { t } = useI18n();

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
          <Link to="/favorites" className="app-icon-button" aria-label={t.header.favorites}>
            ♡
          </Link>
        </div>
      </nav>
    </header>
  );
}
