import { useEffect, useRef, useState } from 'react';
import { apiGet } from '../api/client';
import type { PhoneResponse } from '../api/types';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

type PhoneState = 'idle' | 'loading' | 'done' | 'error';

interface PhoneRevealProps {
  listingId: number;
}

/** «Показать телефон»: номер не лежит в разметке, запрашивается у бэкенда по клику */
export default function PhoneReveal({ listingId }: PhoneRevealProps) {
  const { t } = useI18n();
  const [state, setState] = useState<PhoneState>('idle');
  const [phone, setPhone] = useState('');
  const linkRef = useRef<HTMLAnchorElement>(null);
  const lt = t.listing;

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
    } catch {
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
        className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-hover)] active:scale-[.98] disabled:opacity-70"
        disabled={state === 'loading'}
        aria-busy={state === 'loading'}
        onClick={load}
      >
        {state === 'loading' && <span className="spinner" aria-hidden="true" />}
        {state === 'idle' && <span>📞 {lt.show_phone}</span>}
        {state === 'loading' && <span>{lt.loading}</span>}
        {state === 'error' && <span>↻ {lt.retry}</span>}
      </button>
      {state === 'error' && (
        <p className="text-center text-xs font-medium text-[var(--danger)]" role="alert">
          {lt.phone_error}
        </p>
      )}
    </div>
  );
}
