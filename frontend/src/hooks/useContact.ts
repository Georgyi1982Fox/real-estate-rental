import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiPost } from '../api/client';
import type { ContactResponse, ListingId } from '../api/types';
import { haptic, openLink } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

/**
 * «Написать»: если ссылка на объявление-источник уже известна (sourceUrl), открываем её сразу.
 * Иначе спрашиваем бэкенд ({url}: t.me, внешняя или внутренняя ссылка).
 *
 * Сразу — важно: Telegram открывает внешние ссылки только прямо в ответ на нажатие,
 * после ожидания ответа сервера переход на телефоне молча блокируется.
 */
export function useContact(listingId: ListingId | null, sourceUrl?: string | null) {
  const { t } = useI18n();
  const showToast = useToast();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

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
    } catch {
      showToast(t.listing.write_error, 'error');
      haptic('error');
    } finally {
      setLoading(false);
    }
  }, [listingId, sourceUrl, navigate, showToast, t]);

  return { contact, loading };
}
