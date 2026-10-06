import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, apiGet } from '../api/client';
import type { ListingId, PhoneResponse } from '../api/types';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Modal from './Modal';
import OpenInTelegram from './OpenInTelegram';

type PhoneState = 'idle' | 'loading' | 'done' | 'error' | 'login';

interface PhoneRevealProps {
  listingId: ListingId;
  /** Бэкенд ответил 404: объявление скрыто или снято */
  onGone: () => void;
}

/**
 * «Показать телефон»: номер не лежит в разметке, запрашивается у бэкенда по клику.
 * Номера хозяев бэкенд отдаёт только после входа через Telegram: на 401 кнопка
 * превращается во «Войдите через Telegram…» и открывает модалку входа.
 */
export default function PhoneReveal({ listingId, onGone }: PhoneRevealProps) {
  const { t } = useI18n();
  const [state, setState] = useState<PhoneState>('idle');
  const [phone, setPhone] = useState('');
  const [loginOpen, setLoginOpen] = useState(false);
  const linkRef = useRef<HTMLAnchorElement>(null);
  const lt = t.listing;
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeLogin = useCallback(() => setLoginOpen(false), []);

  useEffect(() => {
    if (state === 'done') linkRef.current?.focus();
  }, [state]);

  const load = async () => {
    setState('loading');
    try {
      const data = await apiGet<PhoneResponse>(`/api/listings/${listingId}/phone`);
      setPhone(data.phone);
      setState('done');
      haptic('success');
    } catch (error) {
      if (error instanceof ApiError && error.isUnauthorized) {
        setState('login');
        setLoginOpen(true);
        return;
      }
      if (error instanceof ApiError && error.isNotFound) {
        onGone();
        return;
      }
      setState('error');
      haptic('error');
    }
  };

  if (state === 'done') {
    return (
      <a
        ref={linkRef}
        href={`tel:${phone.replace(/\s/g, '')}`}
        className="phone-number inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] border border-[var(--primary)] px-4 py-3 text-sm font-semibold text-[var(--primary)] transition-colors hover:bg-[var(--surface-hover)]"
      >
        <span aria-hidden="true">📞</span>
        <span dir="ltr">{phone}</span>
      </a>
    );
  }

  return (
    <div className="listing-contact__phone flex min-w-0 flex-col gap-2">
      <button
        type="button"
        className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-center text-sm font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-hover)] active:scale-[.98] disabled:opacity-70"
        disabled={state === 'loading'}
        aria-busy={state === 'loading'}
        onClick={() => {
          if (state === 'login') setLoginOpen(true);
          else void load();
        }}
      >
        {state === 'loading' && <span className="spinner" aria-hidden="true" />}
        {state === 'idle' && <span>📞 {lt.show_phone}</span>}
        {state === 'loading' && <span>{lt.loading}</span>}
        {state === 'error' && <span>↻ {lt.retry}</span>}
        {state === 'login' && <span>{lt.phone_login}</span>}
      </button>
      {state === 'error' && (
        <p className="text-center text-xs font-medium text-[var(--danger)]" role="alert">
          {lt.phone_error}
        </p>
      )}

      <Modal open={loginOpen} title={lt.show_phone} onClose={closeLogin}>
        <OpenInTelegram plain />
      </Modal>
    </div>
  );
}
