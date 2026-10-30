import { useI18n } from '../providers/I18nProvider';
import ExternalLink from './ExternalLink';

/**
 * «💬 Написать хозяину в боте»: карточка гостиницы в боте, там «✍️ Написать хозяину» —
 * бот переводит переписку, Telegram гостя и хозяина друг другу не виден. url — из
 * GET /api/hotels/{id}/share; в Telegram открывается через openTelegramLink
 */
export default function HotelBotChat({ url }: { url: string }) {
  const { t } = useI18n();
  const ht = t.hotels;

  return (
    <div className="hotel-bot-chat flex min-w-0 flex-col gap-1.5">
      <ExternalLink
        href={url}
        className="hotel-bot-chat__button inline-flex min-h-12 w-full min-w-0 items-center justify-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-center text-sm font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-hover)] active:scale-[.98]"
      >
        <span aria-hidden="true">💬</span>
        {ht.write_bot}
      </ExternalLink>
      <p className="hotel-bot-chat__hint m-0 text-center text-xs text-[var(--text-secondary)]">
        {ht.write_bot_hint}
      </p>
    </div>
  );
}
