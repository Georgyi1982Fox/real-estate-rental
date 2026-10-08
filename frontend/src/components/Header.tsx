import { Link } from 'react-router-dom';
import { useFavorites } from '../hooks/useFavorites';
import { useUnreadNotifications } from '../hooks/useNotificationFeed';
import { LOGO_URL } from '../lib/config';
import { fill } from '../lib/format';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import Avatar from './Avatar';
import type { NavMode } from './BottomNav';
import CountBadge from './CountBadge';
import Icon from './Icon';
import LanguageSwitcher from './LanguageSwitcher';

interface HeaderProps {
  /** Нижняя панель вкладок: «Избранное» уже есть в ней — в шапке его не повторяем */
  nav: NavMode;
}

export default function Header({ nav }: HeaderProps) {
  const { t } = useI18n();
  const { count } = useFavorites();
  const { user, loading } = useAuth();
  const unread = useUnreadNotifications();
  // always — панель на любой ширине, mobile — только до 1024px
  const inNav = nav === 'always';
  const navHidden = nav === 'mobile' ? 'max-lg:hidden' : '';

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
          <span className="truncate text-lg font-bold tracking-tight">bina.ai</span>
        </Link>
        <div className="flex items-center gap-1">
          <LanguageSwitcher />
          {!inNav && (
            <Link
              to="/favorites"
              className={`app-icon-button app-header__favorites relative ${navHidden}`}
              aria-label={count > 0 ? fill(t.header.favorites_count, count) : t.header.favorites}
            >
              <Icon name="heart" className="size-5" />
              <CountBadge count={count} max={99} />
            </Link>
          )}
          {/* Гостю уведомлений нет — колокольчик не показываем */}
          {user && (
            <Link
              to="/notifications"
              className="app-icon-button app-header__notifications relative"
              aria-label={
                unread > 0 ? fill(t.header.notifications_count, unread) : t.header.notifications
              }
            >
              {/* Колокольчик качается, только когда есть непрочитанные */}
              <Icon name="bell" className={`size-5 ${unread > 0 ? 'bell-ring' : ''}`} />
              <CountBadge count={unread} max={9} />
            </Link>
          )}
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
