import { Link } from 'react-router-dom';
import type { AppNotification, NotificationType } from '../api/types';
import { fillVars, formatPrice, timeAgo, tr } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

const TYPE_ICONS: Record<NotificationType, string> = {
  new_listing: '🏠',
  price_drop: '📉',
  system: 'ℹ️',
};

const BODY_CLASS = 'notification-card__body flex w-full items-start gap-3 p-4 text-left';

interface NotificationCardProps {
  notification: AppNotification;
  /** Нажатие по карточке: отметить прочитанным (переход на квартиру делает сама ссылка) */
  onRead: () => void;
}

/**
 * Карточка уведомления: иконка типа, текст, фото квартиры, время.
 * new_listing / price_drop ведут на /listing/{id}; system — кнопка «прочитать».
 */
export default function NotificationCard({ notification, onRead }: NotificationCardProps) {
  const { t, lang } = useI18n();
  const nt = t.notifications;
  const { listing, is_read: isRead } = notification;

  // Текст собираем на фронтенде — сервер присылает только данные
  let text = '';
  let note = '';
  if (notification.type === 'new_listing' && listing) {
    text = fillVars(nt.new_listing, {
      title: tr(listing.title, lang),
      price: formatPrice(listing.price, listing.currency),
    });
    if (notification.search_name) note = fillVars(nt.by_search, { name: notification.search_name });
  } else if (notification.type === 'price_drop' && listing) {
    text = fillVars(nt.price_drop, {
      old: formatPrice(notification.old_price, listing.currency),
      price: formatPrice(listing.price, listing.currency),
    });
    note = tr(listing.title, lang);
  } else {
    text = tr(notification.text, lang);
  }

  const content = (
    <>
      <span
        className="notification-card__icon grid size-10 shrink-0 place-items-center rounded-full bg-[var(--surface-hover)] text-lg"
        aria-hidden="true"
      >
        {TYPE_ICONS[notification.type]}
      </span>
      <span className="notification-card__text flex min-w-0 flex-1 flex-col gap-1">
        <span
          className={`text-sm leading-snug break-words ${isRead ? 'text-[var(--text-primary)]' : 'font-semibold text-[var(--text-primary)]'}`}
        >
          {text}
        </span>
        {note && (
          <span className="notification-card__note line-clamp-2 text-[13px] text-[var(--text-secondary)]">
            {note}
          </span>
        )}
        <time
          className="notification-card__time text-xs text-[var(--text-secondary)]"
          dateTime={notification.created_at}
        >
          {timeAgo(notification.created_at, lang)}
        </time>
      </span>
      {listing?.image && (
        <img
          className="notification-card__image size-16 shrink-0 rounded-[var(--radius-sm)] bg-[var(--surface-hover)] object-cover"
          src={listing.image}
          alt=""
          loading="lazy"
          width={64}
          height={64}
        />
      )}
      {!isRead && (
        <span className="notification-card__dot mt-1.5 size-2.5 shrink-0 rounded-full bg-[var(--primary)]">
          <span className="sr-only">{nt.unread}</span>
        </span>
      )}
    </>
  );

  const handleClick = () => {
    haptic('light');
    onRead();
  };

  let body;
  if (listing && notification.type !== 'system') {
    body = (
      <Link
        to={`/listing/${encodeURIComponent(listing.id)}`}
        className={`${BODY_CLASS} hover:bg-[var(--surface-hover)]`}
        onClick={handleClick}
      >
        {content}
      </Link>
    );
  } else if (!isRead) {
    body = (
      <button
        type="button"
        className={`${BODY_CLASS} hover:bg-[var(--surface-hover)]`}
        onClick={handleClick}
      >
        {content}
      </button>
    );
  } else {
    // Прочитанное служебное уведомление — просто текст, нажимать нечего
    body = <div className={BODY_CLASS}>{content}</div>;
  }

  return (
    <article
      className={`notification-card overflow-hidden rounded-[var(--radius-lg)] border shadow-[var(--shadow-sm)] transition-colors duration-200 ${
        isRead
          ? 'border-[var(--border)] bg-[var(--surface)]'
          : 'notification-card--unread border-[var(--primary)]/25 bg-[var(--primary)]/5'
      }`}
    >
      {body}
    </article>
  );
}
