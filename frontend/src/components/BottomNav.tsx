import { NavLink } from 'react-router-dom';
import { useFavorites } from '../hooks/useFavorites';
import type { Strings } from '../i18n/strings';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import CountBadge from './CountBadge';
import Icon from './Icon';
import type { IconName } from './Icon';

/**
 * Где видна панель: mobile — до 1024px (в браузере на компьютере навигация в шапке),
 * always — в Telegram на любой ширине, none — панели нет.
 */
export type NavMode = 'none' | 'mobile' | 'always';

interface Tab {
  key: Exclude<keyof Strings['nav'], 'label'>;
  to: string;
  icon: IconName;
}

const TABS: Tab[] = [
  { key: 'home', to: '/', icon: 'home' },
  { key: 'search', to: '/search', icon: 'search' },
  { key: 'favorites', to: '/favorites', icon: 'heart' },
  { key: 'rent_out', to: '/my-listings', icon: 'home_plus' },
  { key: 'profile', to: '/profile', icon: 'user' },
];

const FAVORITES_BADGE_MAX = 99;

interface BottomNavProps {
  mode: Exclude<NavMode, 'none'>;
}

/** Нижняя панель вкладок: Главная · Поиск · Избранное · Сдать · Профиль */
export default function BottomNav({ mode }: BottomNavProps) {
  const { t } = useI18n();
  const { count } = useFavorites();

  return (
    <nav
      className={`bottom-nav ${mode === 'mobile' ? 'bottom-nav--mobile' : ''} fixed inset-x-0 bottom-0 z-30 border-t border-[var(--border)] bg-[var(--surface)]/90 pb-[var(--safe-bottom)] pl-[var(--safe-left)] pr-[var(--safe-right)] backdrop-blur-md`}
      aria-label={t.nav.label}
    >
      <ul className="bottom-nav__list mx-auto flex w-full max-w-screen-sm px-1">
        {TABS.map((tab) => (
          <li key={tab.key} className="min-w-0 flex-1">
            <NavLink
              to={tab.to}
              end
              className={({ isActive }) =>
                `bottom-nav__tab flex min-h-14 flex-col items-center justify-center gap-0.5 rounded-[var(--radius-md)] px-0.5 text-[11px] leading-tight active:scale-[.97] ${
                  isActive
                    ? 'bottom-nav__tab--active font-semibold text-[var(--text-primary)]'
                    : 'font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`
              }
              onClick={() => haptic('selection')}
            >
              {({ isActive }) => (
                <>
                  {/* Активная вкладка — иконка на подложке цвета бренда */}
                  <span
                    className={`bottom-nav__icon relative inline-grid h-7 w-12 place-items-center rounded-full transition-colors duration-200 ${
                      isActive ? 'bg-[var(--primary)]/20' : ''
                    }`}
                  >
                    <Icon name={tab.icon} className="size-5" />
                    {tab.key === 'favorites' && (
                      <CountBadge count={count} max={FAVORITES_BADGE_MAX} />
                    )}
                  </span>
                  <span className="max-w-full truncate">{t.nav[tab.key]}</span>
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
