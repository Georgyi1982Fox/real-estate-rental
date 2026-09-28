import { Link } from 'react-router-dom';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Icon from '../components/Icon';
import NotificationCard from '../components/NotificationCard';
import NotificationSkeleton from '../components/NotificationSkeleton';
import OpenInTelegram from '../components/OpenInTelegram';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useNotificationFeed } from '../hooks/useNotificationFeed';
import type { NotificationFilter } from '../hooks/useNotificationFeed';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

const SKELETON_COUNT = 4;

const PRIMARY_BUTTON_CLASS =
  'inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]';

export default function NotificationsPage() {
  const { t } = useI18n();
  const nt = t.notifications;
  const showToast = useToast();
  const feed = useNotificationFeed();
  const { items, unreadCount, filter, loading, error, unauthorized } = feed;

  useDocumentTitle(`${nt.page_title} — Bina.ai`);
  useTelegramBackButton('/');

  const tabs: { value: NotificationFilter; label: string; count?: number }[] = [
    { value: 'all', label: nt.tab_all },
    { value: 'unread', label: nt.tab_unread, count: unreadCount },
  ];

  const readAll = async () => {
    haptic('light');
    if (!(await feed.markAllRead())) return;
    showToast(nt.read_all_toast, 'success');
    haptic('success');
  };

  let content;
  if (unauthorized) {
    content = (
      <section className="notifications__guest mx-auto w-full max-w-sm py-4">
        <OpenInTelegram />
      </section>
    );
  } else if (loading) {
    content = (
      <ul className="notifications__list flex flex-col gap-3">
        {Array.from({ length: SKELETON_COUNT }, (_, index) => (
          <li key={index}>
            <NotificationSkeleton />
          </li>
        ))}
      </ul>
    );
  } else if (error) {
    content = <ErrorState onRetry={feed.reload} />;
  } else if (items.length === 0) {
    content = (
      <EmptyState icon="🔔" title={nt.empty_title} text={nt.empty_text}>
        <Link to="/searches" className={PRIMARY_BUTTON_CLASS}>
          {nt.to_searches}
        </Link>
      </EmptyState>
    );
  } else {
    content = (
      <>
        <ul className="notifications__list flex flex-col gap-3">
          {items.map((notification) => (
            <li key={notification.id}>
              <NotificationCard
                notification={notification}
                onRead={() => void feed.markRead(notification.id)}
              />
            </li>
          ))}
        </ul>
        {feed.hasMore && (
          <button
            type="button"
            className="notifications__more mx-auto inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-5 py-2.5 text-sm font-semibold transition-colors hover:bg-[var(--surface-hover)] disabled:opacity-60"
            disabled={feed.loadingMore}
            aria-busy={feed.loadingMore}
            onClick={() => {
              haptic('light');
              void feed.loadMore();
            }}
          >
            {feed.loadingMore ? '…' : nt.show_more}
          </button>
        )}
      </>
    );
  }

  return (
    <section
      className="notifications mx-auto flex w-full max-w-2xl flex-col gap-5 py-2 sm:py-4"
      aria-labelledby="notifications-title"
      aria-busy={loading}
    >
      <header className="notifications__header flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <h1 id="notifications-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
          {nt.heading}
        </h1>
        {!unauthorized && (
          <Link
            to="/searches"
            className="notifications__searches inline-flex min-h-11 items-center gap-1 rounded-[var(--radius-sm)] text-sm font-medium text-[var(--primary)] hover:text-[var(--primary-hover)]"
            onClick={() => haptic('light')}
          >
            {t.header.searches}
            <Icon name="chevron" className="size-4" />
          </Link>
        )}
      </header>

      {!unauthorized && (
        <nav
          className="notifications__toolbar flex flex-wrap items-center justify-between gap-3"
          aria-label={nt.filter}
        >
          <ul className="notifications__tabs flex gap-1 rounded-[var(--radius-md)] bg-[var(--surface-hover)] p-1">
            {tabs.map((tab) => {
              const active = tab.value === filter;
              return (
                <li key={tab.value}>
                  <button
                    type="button"
                    className={`notifications__tab inline-flex min-h-9 items-center gap-2 rounded-[var(--radius-sm)] px-3 py-1.5 text-sm font-medium transition-colors duration-200 ${
                      active
                        ? 'bg-[var(--surface)] text-[var(--text-primary)] shadow-[var(--shadow-sm)]'
                        : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                    }`}
                    aria-pressed={active}
                    onClick={() => {
                      if (active) return;
                      haptic('light');
                      feed.setFilter(tab.value);
                    }}
                  >
                    {tab.label}
                    {tab.count !== undefined && tab.count > 0 && (
                      <span className="notifications__tab-count inline-flex min-h-5 min-w-5 items-center justify-center rounded-full bg-[var(--primary)] px-1.5 text-[11px] font-bold leading-none text-white">
                        {tab.count > 99 ? '99+' : tab.count}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
          {unreadCount > 0 && !loading && (
            <button
              type="button"
              className="notifications__read-all inline-flex min-h-11 items-center gap-1.5 rounded-[var(--radius-sm)] px-2 text-sm font-medium text-[var(--primary)] hover:text-[var(--primary-hover)]"
              onClick={() => void readAll()}
            >
              <Icon name="check" className="size-4" />
              {nt.read_all}
            </button>
          )}
        </nav>
      )}

      {content}
    </section>
  );
}
