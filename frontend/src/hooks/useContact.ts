import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiPost } from '../api/client';
import type { ContactResponse } from '../api/types';
import { haptic, openLink } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

/** «Написать»: бэкенд возвращает {url}, куда вести пользователя (t.me, внешняя или внутренняя ссылка) */
export function useContact(listingId: number | null) {
  const { t } = useI18n();
  const showToast = useToast();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const contact = useCallback(async () => {
    if (listingId === null) return;
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
  }, [listingId, navigate, showToast, t]);

  return { contact, loading };
}
