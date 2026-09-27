import { Link } from 'react-router-dom';
import { useFavorites } from '../hooks/useFavorites';
import { LOGO_URL } from '../lib/config';
import { fill } from '../lib/format';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import Avatar from './Avatar';
import LanguageSwitcher from './LanguageSwitcher';

export default function Header() {
  const { t } = useI18n();
  const { count } = useFavorites();
  const { user, loading } = useAuth();

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
          {/* Тот же logo.svg, что и favicon; alt пустой — название рядом текстом */}
          <img
            className="app-header__logo medallion medallion--logo size-10 shrink-0 rounded-full shadow-[var(--shadow-sm)]"
            src={LOGO_URL}
            alt=""
            width={40}
            height={40}
          />
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
          {user ? (
            <Link
              to="/profile"
              className="app-header__avatar inline-grid min-h-10 min-w-10 place-items-center rounded-full hover:opacity-85 active:scale-[0.97]"
              aria-label={fill(t.header.profile, user.first_name || user.username || '')}
            >
              <Avatar user={user} className="medallion size-8 text-sm" />
            </Link>
          ) : loading ? (
            // Ждём /api/auth/me — место под аватар, чтобы шапка не прыгала
            <span
              className="app-header__avatar-skeleton mx-1 size-8 animate-pulse rounded-full bg-[var(--surface-hover)]"
              aria-hidden="true"
            />
          ) : (
            <Link
              to="/auth"
              className="app-icon-button app-header__login"
              aria-label={t.header.login}
            >
              {/* Lucide «circle-user» */}
              <svg
                className="medallion size-6"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="10" />
                <circle cx="12" cy="10" r="3" />
                <path d="M7 20.662V19a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v1.662" />
              </svg>
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
