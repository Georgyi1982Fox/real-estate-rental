import { useParams } from 'react-router-dom';
import type { LegalDocId, LegalDocument } from '../api/types';
import Accordion from '../components/Accordion';
import ErrorState from '../components/ErrorState';
import { useApi } from '../hooks/useApi';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { useI18n } from '../providers/I18nProvider';
import NotFoundPage from './NotFoundPage';

const SKELETON_ROWS = 5;

function isLegalDoc(value: string): value is LegalDocId {
  return value === 'terms' || value === 'privacy';
}

/** Документы сервиса: /legal/terms и /legal/privacy на текущем языке сайта */
export default function LegalPage() {
  const { doc = '' } = useParams();
  const { lang, t } = useI18n();
  const docId = isLegalDoc(doc) ? doc : null;
  const { data, error, loading, reload } = useApi<LegalDocument>(
    docId ? `/api/legal/${docId}?lang=${lang}` : null,
  );
  // Заголовок с бэкенда важнее; не пришёл — из словаря
  const title = data?.title?.trim() || (docId ? t.legal.titles[docId] : '');

  useDocumentTitle(title ? `${title} — bina.ai` : 'bina.ai');
  useTelegramBackButton('/');

  if (!docId || error?.isNotFound) return <NotFoundPage />;

  return (
    <article
      className="legal mx-auto flex w-full max-w-2xl flex-col gap-6 py-2 sm:py-4"
      aria-labelledby="legal-title"
      aria-busy={loading}
    >
      <header className="legal__header flex flex-col gap-2">
        <h1 id="legal-title" className="break-words text-2xl font-bold tracking-tight sm:text-3xl">
          {title}
        </h1>
        {data?.version_label && (
          <p className="legal__version text-xs text-[var(--text-secondary)]">
            {data.version_label}
          </p>
        )}
      </header>

      {loading && (
        <ul className="legal__skeleton flex flex-col gap-2" aria-hidden="true">
          {Array.from({ length: SKELETON_ROWS }, (_, index) => (
            <li
              key={index}
              className="h-12 animate-pulse rounded-[var(--radius-md)] bg-[var(--surface-hover)]"
            />
          ))}
        </ul>
      )}

      {error && <ErrorState onRetry={reload} />}

      {data && (
        <>
          {data.intro && (
            <p className="legal__intro whitespace-pre-line text-sm leading-relaxed text-[var(--text-secondary)] sm:text-base">
              {data.intro}
            </p>
          )}
          <section className="legal__sections" aria-label={t.legal.sections}>
            <Accordion items={data.sections} openIndex={0} />
          </section>
        </>
      )}
    </article>
  );
}
