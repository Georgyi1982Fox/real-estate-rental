import { Link } from 'react-router-dom';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useI18n } from '../providers/I18nProvider';

export default function NotFoundPage() {
  const { t } = useI18n();
  useDocumentTitle(`${t.common.not_found_title} — Bina.ai`);

  return (
    <section className="not-found flex flex-col items-center gap-3 py-16 text-center" aria-labelledby="not-found-title">
      <span className="text-4xl" aria-hidden="true">
        🔍
      </span>
      <h1 id="not-found-title" className="text-2xl font-bold tracking-tight">
        {t.common.not_found_title}
      </h1>
      <p className="max-w-sm text-sm text-[var(--text-secondary)]">{t.common.not_found_text}</p>
      <Link
        to="/"
        className="mt-2 inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)]"
      >
        {t.common.to_home}
      </Link>
    </section>
  );
}
