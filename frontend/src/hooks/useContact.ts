import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, apiPost } from '../api/client';
import type { ContactResponse, ListingId } from '../api/types';
import { haptic, openLink } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

/**
 * «Написать»: если ссылка на объявление-источник уже известна (sourceUrl), открываем её сразу.
 * Иначе спрашиваем бэкенд ({url}: t.me, внешняя или внутренняя ссылка).
 * Ответ 404 — объявление скрыто или снято: gone = true, кнопки связи убираем.
 *
 * Сразу — важно: Telegram открывает внешние ссылки только прямо в ответ на нажатие,
 * после ожидания ответа сервера переход на телефоне молча блокируется.
 */
export function useContact(listingId: ListingId | null, sourceUrl?: string | null) {
  const { t } = useI18n();
  const showToast = useToast();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  // ID, а не флаг: хук живёт дольше страницы одного объявления (переход на похожее)
  const [goneId, setGoneId] = useState<ListingId | null>(null);

  const contact = useCallback(async () => {
    if (listingId === null) return;
    if (sourceUrl) {
      openLink(sourceUrl, (path) => navigate(path));
      return;
    }
    setLoading(true);
    try {
      const { url } = await apiPost<ContactResponse>(`/api/listings/${listingId}/contact`);
      openLink(url, (path) => navigate(path));
    } catch (error) {
      if (error instanceof ApiError && error.isNotFound) {
        setGoneId(listingId);
        return;
      }
      showToast(t.listing.write_error, 'error');
      haptic('error');
    } finally {
      setLoading(false);
    }
  }, [listingId, sourceUrl, navigate, showToast, t]);

  return { contact, loading, gone: goneId !== null && goneId === listingId };
}
