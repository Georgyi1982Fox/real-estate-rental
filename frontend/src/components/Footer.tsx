import { Link } from 'react-router-dom';
import { MORE_PATH } from '../lib/paths';
import { useI18n } from '../providers/I18nProvider';
import type { NavMode } from './BottomNav';

const NAV_CLASS: Record<NavMode, string> = {
  none: '',
  mobile: 'app-footer--nav app-footer--nav-mobile',
  always: 'app-footer--nav',
};

interface FooterProps {
  /** Нижняя панель вкладок: подвал оставляет под неё место, «Ещё» уже есть в панели */
  nav: NavMode;
}

export default function Footer({ nav }: FooterProps) {
  const { t } = useI18n();

  return (
    <footer
      className={`app-footer ${NAV_CLASS[nav]} border-t border-[var(--border)] bg-[var(--surface)]`}
    >
      <nav
        className="mx-auto flex max-w-screen-xl items-center justify-between px-4 py-5 text-xs text-[var(--text-secondary)] sm:px-6 lg:px-8"
        aria-label={t.footer.nav}
      >
        <span>© {new Date().getFullYear()} bina.ai</span>
        {nav !== 'always' && (
          <span className={`flex items-center gap-1 ${nav === 'mobile' ? 'max-lg:hidden' : ''}`}>
            <Link to={MORE_PATH} className="rounded-md px-2 py-1">
              {t.footer.more}
            </Link>
            <Link to="/profile" className="rounded-md px-2 py-1">
              {t.footer.profile}
            </Link>
          </span>
        )}
      </nav>
    </footer>
  );
}
