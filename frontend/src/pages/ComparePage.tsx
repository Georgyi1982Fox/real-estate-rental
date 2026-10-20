import { Link } from 'react-router-dom';
import type { ListingComparison, ListingId } from '../api/types';
import CompareTable from '../components/CompareTable';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Icon from '../components/Icon';
import OpenInTelegram from '../components/OpenInTelegram';
import { useApi } from '../hooks/useApi';
import { useCompare } from '../hooks/useCompare';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useGoBack, useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { COMPARE_MIN, compareApiPath } from '../lib/compare';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';

const LIST_PATH = '/search';

const BUTTON_CLASS =
  'inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]';

/**
 * Сравнение квартир (FRONTEND-027): 2-3 квартиры, отмеченные «⚖ Сравнить» в поиске
 * или избранном. Сервер отвечает только вошедшим — гостю предлагаем войти через Telegram
 */
export default function ComparePage() {
  const { t } = useI18n();
  const ct = t.compare;
  const { user, loading: authLoading } = useAuth();
  const { ids, remove, clear } = useCompare();
  const goBack = useGoBack(LIST_PATH);
  const ready = ids.length >= COMPARE_MIN;
  const { data, error, loading, reload } = useApi<ListingComparison>(
    user && ready ? compareApiPath(ids) : null,
  );

  useDocumentTitle(`${ct.title} — bina.ai`);
  useTelegramBackButton(LIST_PATH);

  // Осталась одна квартира — сравнивать нечего, возвращаемся к списку
  const removeListing = (id: ListingId) => {
    const left = ids.filter((item) => item !== String(id)).length;
    remove(id);
    if (left < COMPARE_MIN) goBack();
  };

  // 404 — одной из квартир больше нет, 422 — сервер не принял выбор (например, устарел)
  const gone = error?.status === 404 || error?.status === 422;
  const guest = (!user && !authLoading) || error?.isUnauthorized === true;

  let content;
  if (!ready) {
    content = (
      <EmptyState
        icon="⚖️"
        title={ids.length === 0 ? ct.empty_title : ct.one_title}
        text={ids.length === 0 ? ct.empty_text : ct.one_text}
      >
        <Link to={LIST_PATH} className={BUTTON_CLASS}>
          {ct.find}
        </Link>
      </EmptyState>
    );
  } else if (guest) {
    content = (
      <div className="mx-auto w-full max-w-md">
        <OpenInTelegram />
      </div>
    );
  } else if (gone) {
    content = (
      <EmptyState icon="⚖️" title={ct.gone}>
        <button type="button" className={BUTTON_CLASS} onClick={clear}>
          {ct.clear}
        </button>
      </EmptyState>
    );
  } else if (error) {
    content = <ErrorState onRetry={reload} />;
  } else if (loading || authLoading || !data) {
    content = (
      <div
        className="compare-page__skeleton h-96 animate-pulse rounded-[var(--radius-lg)] bg-[var(--surface-hover)]"
        aria-hidden="true"
      />
    );
  } else {
    content = (
      <>
        <CompareTable data={data} onRemove={removeListing} />
        <p className="compare-page__note m-0 text-xs leading-5 text-[var(--text-secondary)]">
          {ct.note}
        </p>
      </>
    );
  }

  return (
    <section
      className="compare-page flex flex-col gap-4"
      aria-labelledby="compare-title"
      aria-busy={loading}
    >
      <nav className="compare-page__breadcrumb" aria-label={ct.back}>
        <Link
          to={LIST_PATH}
          className="inline-flex min-h-9 items-center gap-1 rounded-[var(--radius-sm)] text-sm font-medium text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
          onClick={(event) => {
            if (event.metaKey || event.ctrlKey || event.shiftKey) return;
            event.preventDefault();
            haptic('light');
            goBack();
          }}
        >
          <span aria-hidden="true">←</span> {ct.back}
        </Link>
      </nav>
      <header className="compare-page__header space-y-1">
        <h1
          id="compare-title"
          className="flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl"
        >
          <Icon name="scale" className="size-7" />
          {ct.title}
        </h1>
        {ready && data && !error && (
          <p className="m-0 text-sm text-[var(--text-secondary)]">{ct.intro}</p>
        )}
      </header>
      {content}
    </section>
  );
}
