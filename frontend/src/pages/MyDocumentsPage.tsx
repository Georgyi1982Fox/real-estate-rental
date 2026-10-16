import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, apiGet } from '../api/client';
import type { DocumentSent, SignedDocuments } from '../api/types';
import DocumentCard from '../components/DocumentCard';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Icon from '../components/Icon';
import OpenInTelegram from '../components/OpenInTelegram';
import SavedSearchSkeleton from '../components/SavedSearchSkeleton';
import { useApi } from '../hooks/useApi';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { ACCEPTANCE_PATH } from '../lib/acceptance';
import { documentFilePath } from '../lib/signing';
import type { DocumentPart } from '../lib/signing';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

const SKELETON_COUNT = 2;
const LINK_CLASS =
  'inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-2.5 text-sm font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-hover)] active:scale-[.98]';

/** Какой файл какого документа сейчас запрашивается у бота */
interface Busy {
  id: string;
  part: DocumentPart;
}

/**
 * «Мои документы» (FRONTEND-042): договоры и акты, отправленные на подпись, — свои и те,
 * что человек подписал как вторая сторона. Файл и сертификат бот присылает в чат
 */
export default function MyDocumentsPage() {
  const { t } = useI18n();
  const st = t.signing;
  const showToast = useToast();
  const { user, loading: authLoading } = useAuth();
  const { data, error, loading, reload } = useApi<SignedDocuments>(user ? '/api/documents' : null);
  const [busy, setBusy] = useState<Busy | null>(null);
  // Состояние обновится только на следующем рендере, а двойное нажатие приходит раньше
  const pending = useRef(false);

  useDocumentTitle(`${st.title} — bina.ai`);
  useTelegramBackButton('/profile');

  const requestFile = async (id: string, part: DocumentPart) => {
    if (pending.current) return;
    pending.current = true;
    haptic('light');
    setBusy({ id, part });
    try {
      const result = await apiGet<DocumentSent>(documentFilePath(id, part));
      if (!result.sent) throw new Error('not sent');
      haptic('success');
      showToast(st.file_sent, 'success');
    } catch (failure) {
      haptic('error');
      if (failure instanceof ApiError && failure.isUnauthorized) {
        // Сессия закончилась: повторный запрос списка ответит 401 и покажет вход
        reload();
      } else if (failure instanceof ApiError && (failure.isNotFound || failure.status === 409)) {
        // Документ удалён или ещё не подписан обеими сторонами — список устарел
        showToast(failure.isNotFound ? st.errors.not_found : st.errors.not_signed, 'error');
        reload();
      } else if (failure instanceof ApiError && failure.status === 502) {
        showToast(t.contract.errors.bot, 'error');
      } else {
        showToast(t.contract.errors.failed, 'error');
      }
    } finally {
      pending.current = false;
      setBusy(null);
    }
  };

  if ((!user && !authLoading) || error?.isUnauthorized) {
    return (
      <section className="my-documents mx-auto w-full max-w-md py-6">
        <OpenInTelegram />
      </section>
    );
  }

  const documents = data?.items ?? [];

  return (
    <section
      className="my-documents mx-auto flex w-full max-w-2xl flex-col gap-6"
      aria-labelledby="my-documents-title"
    >
      <header className="my-documents__header space-y-1 py-2 sm:py-4">
        <h1 id="my-documents-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
          {st.title}
        </h1>
        <p className="m-0 text-sm text-[var(--text-secondary)]">{st.intro}</p>
      </header>

      {(loading || authLoading) && (
        <ul className="m-0 flex list-none flex-col gap-4 p-0" aria-hidden="true">
          {Array.from({ length: SKELETON_COUNT }, (_, index) => (
            <li key={index}>
              <SavedSearchSkeleton />
            </li>
          ))}
        </ul>
      )}

      {error && <ErrorState onRetry={reload} />}

      {data && documents.length === 0 && (
        <EmptyState icon="📄" title={st.empty_title} text={st.empty_text}>
          <div className="mt-2 flex flex-wrap justify-center gap-2">
            <Link to={ACCEPTANCE_PATH} className={LINK_CLASS} onClick={() => haptic('light')}>
              <Icon name="list_checks" className="size-4" />
              {t.acceptance.title}
            </Link>
            <Link to="/search" className={LINK_CLASS} onClick={() => haptic('light')}>
              <Icon name="search" className="size-4" />
              {t.favorites.find}
            </Link>
          </div>
        </EmptyState>
      )}

      {documents.length > 0 && (
        <>
          <ul className="m-0 flex list-none flex-col gap-4 p-0">
            {documents.map((document) => (
              <li key={document.id}>
                <DocumentCard
                  document={document}
                  busyPart={busy?.id === document.id ? busy.part : null}
                  onFile={(part) => void requestFile(document.id, part)}
                />
              </li>
            ))}
          </ul>
          <p className="my-documents__legal m-0 rounded-[var(--radius-md)] bg-[var(--surface-hover)] p-3 text-xs leading-relaxed text-[var(--text-secondary)]">
            {st.legal_note}
          </p>
        </>
      )}
    </section>
  );
}
