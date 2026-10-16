import type { ListingId, ListingShare } from '../api/types';
import { useApi } from '../hooks/useApi';
import { getWebApp, haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

/**
 * «📤 Поделиться» на странице квартиры (FRONTEND-041). Ссылку берём заранее: так кнопка
 * появляется, только когда делиться есть чем (503 — бот не настроен, 404 — квартира снята),
 * а окно «Поделиться» в браузере открывается прямо по нажатию, без ожидания сети
 */
export default function ShareButton({ listingId }: { listingId: ListingId }) {
  const { lang, t } = useI18n();
  const showToast = useToast();
  const { data: share } = useApi<ListingShare>(
    `/api/listings/${encodeURIComponent(String(listingId))}/share?lang=${lang}`,
  );

  if (!share) return null;

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(share.url);
      haptic('success');
      showToast(t.share.copied, 'success');
    } catch {
      // Буфер обмена недоступен — окно Telegram «Переслать» в новой вкладке
      window.open(share.telegram_url, '_blank', 'noopener,noreferrer');
    }
  };

  const onShare = async () => {
    haptic('light');
    // В Telegram — окно «Переслать» с выбором чата
    const webApp = getWebApp();
    if (webApp) {
      try {
        webApp.openTelegramLink(share.telegram_url);
        return;
      } catch {
        // Старый клиент без openTelegramLink — скопируем ссылку
      }
    }
    if (typeof navigator.share === 'function') {
      try {
        await navigator.share({ title: share.text, text: share.text, url: share.url });
        return;
      } catch (error) {
        // Человек закрыл окно сам — больше ничего не делаем
        if (error instanceof DOMException && error.name === 'AbortError') return;
      }
    }
    await copyLink();
  };

  return (
    <button
      type="button"
      className="listing-share inline-flex min-h-9 items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-sm font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-hover)] active:scale-[.98]"
      aria-label={t.share.label}
      onClick={() => void onShare()}
    >
      <span aria-hidden="true">📤</span>
      <span>{t.share.button}</span>
    </button>
  );
}
