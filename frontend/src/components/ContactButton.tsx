import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiPost } from '../api/client';
import type { ContactResponse } from '../api/types';
import { haptic, openLink } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

interface ContactButtonProps {
  listingId: number;
}

/** «Написать»: бэкенд возвращает {url}, куда вести пользователя (t.me, внешняя или внутренняя ссылка) */
export default function ContactButton({ listingId }: ContactButtonProps) {
  const { t } = useI18n();
  const showToast = useToast();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const contact = async () => {
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
  };

  return (
    <button
      type="button"
      className="listing-contact__write inline-flex min-h-12 items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-4 py-3 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98] disabled:opacity-70"
      disabled={loading}
      aria-busy={loading}
      onClick={contact}
    >
      {loading ? <span className="spinner" aria-hidden="true" /> : <span aria-hidden="true">💬</span>}
      {t.listing.write}
    </button>
  );
}
