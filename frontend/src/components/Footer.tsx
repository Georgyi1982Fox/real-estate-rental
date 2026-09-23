import { Link } from 'react-router-dom';
import { useI18n } from '../providers/I18nProvider';

export default function Footer() {
  const { t } = useI18n();

  return (
    <footer className="app-footer border-t border-[var(--border)] bg-[var(--surface)]">
      <nav
        className="mx-auto flex max-w-screen-xl items-center justify-between px-4 py-5 text-xs text-[var(--text-secondary)] sm:px-6 lg:px-8"
        aria-label={t.footer.nav}
      >
        <span>© {new Date().getFullYear()} Bina.ai</span>
        <Link to="/profile" className="rounded-md px-2 py-1">
          {t.footer.profile}
        </Link>
      </nav>
    </footer>
  );
}
