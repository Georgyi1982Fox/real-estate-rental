import { useCallback, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiDelete } from '../api/client';
import type { ViewHistory } from '../api/types';
import ConfirmDialog from '../components/ConfirmDialog';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Icon from '../components/Icon';
import ListingCard from '../components/ListingCard';
import OpenInTelegram from '../components/OpenInTelegram';
import Skeleton from '../components/Skeleton';
import { forgetResponses, useApi } from '../hooks/useApi';
import { useDistricts } from '../hooks/useDistricts';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { fill, listingTime } from '../lib/format';
import { HISTORY_API, PAGE_HISTORY_LIMIT, historyApiPath } from '../lib/history';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

const SKELETON_COUNT = 3;
const GRID_CLASS = 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';

/** «🕘 Недавно смотрели» (FRONTEND-043): все открытые квартиры, новые сверху, и «Очистить» */
export default function HistoryPage() {
  const { lang, t } = useI18n();
  const ht = t.history;
  const showToast = useToast();
  const { user, loading: authLoading } = useAuth();
  const { names } = useDistricts();
  const { data, error, loading, reload } = useApi<ViewHistory>(
    user ? historyApiPath(PAGE_HISTORY_LIMIT) : null,
  );
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [clearing, setClearing] = useState(false);
  // Двойное нажатие приходит раньше, чем обновится состояние
  const pending = useRef(false);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeConfirm = useCallback(() => setConfirmOpen(false), []);

  useDocumentTitle(`${ht.title} — bina.ai`);
  useTelegramBackButton('/profile');

  const clear = async () => {
    if (pending.current) return;
    pending.current = true;
    setClearing(true);
    try {
      await apiDelete(HISTORY_API);
      // Лента на главной тоже пустая — запомненный ответ не должен мелькнуть
      forgetResponses(HISTORY_API);
      haptic('success');
      showToast(ht.cleared, 'success');
      setConfirmOpen(false);
      reload();
    } catch {
      haptic('error');
      showToast(ht.clear_error, 'error');
    } finally {
      pending.current = false;
      setClearing(false);
    }
  };

  if ((!user && !authLoading) || error?.isUnauthorized) {
    return (
      <section className="history mx-auto w-full max-w-md py-6">
        <OpenInTelegram />
      </section>
    );
  }

  const items = data?.items ?? [];

  return (
    <section className="history flex flex-col gap-6" aria-labelledby="history-title">
      <header className="history__header flex flex-wrap items-start justify-between gap-3 py-2 sm:py-4">
        <div className="min-w-0 space-y-1">
          <h1 id="history-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
            {ht.title}
          </h1>
          <p className="m-0 text-sm text-[var(--text-secondary)]">{ht.intro}</p>
        </div>
        {items.length > 0 && (
          <button
            type="button"
            className="history__clear inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-2.5 text-sm font-semibold text-[var(--danger)] hover:bg-[var(--surface-hover)] active:scale-[.98]"
            aria-haspopup="dialog"
            onClick={() => {
              haptic('light');
              setConfirmOpen(true);
            }}
          >
            <Icon name="trash" className="size-4" />
            {ht.clear}
          </button>
        )}
      </header>

      {(loading || authLoading) && (
        <div className={GRID_CLASS} aria-hidden="true">
          {Array.from({ length: SKELETON_COUNT }, (_, index) => (
            <Skeleton key={index} />
          ))}
        </div>
      )}

      {error && <ErrorState onRetry={reload} />}

      {data && items.length === 0 && (
        <EmptyState icon="🕘" title={ht.empty_title} text={ht.empty_text}>
          <Link
            to="/search"
            className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]"
          >
            {t.favorites.find}
          </Link>
        </EmptyState>
      )}

      {items.length > 0 && (
        <ul className={`history__list m-0 list-none p-0 ${GRID_CLASS}`}>
          {items.map(({ listing, viewed_at: viewedAt }) => (
            <li key={listing.id} className="history__item flex min-w-0 flex-col gap-1.5">
              <ListingCard listing={listing} districtNames={names} />
              <time
                dateTime={viewedAt}
                className="history__viewed px-1 text-xs text-[var(--text-secondary)]"
              >
                {fill(ht.viewed, listingTime(viewedAt, lang, t.listing.hours_ago))}
              </time>
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={confirmOpen}
        title={ht.clear_title}
        text={ht.clear_text}
        confirmLabel={ht.clear}
        danger
        busy={clearing}
        onConfirm={() => void clear()}
        onClose={closeConfirm}
      />
    </section>
  );
}
