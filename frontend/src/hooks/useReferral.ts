import { useCallback, useEffect, useSyncExternalStore } from 'react';
import { ApiError, apiPost } from '../api/client';
import type { ReferralApplyRequest, ReferralApplyResponse } from '../api/types';
import { REFERRAL_APPLY_API, referralStartCode } from '../lib/referral';
import { usesServerFavorites } from '../lib/session';
import { getStartParam } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';

// Мини-апп открыли по ссылке друга (FRONTEND-029): код отправляем на бэкенд один раз,
// итог помним на устройстве — и чтобы не слать повторно, и для плашки «Вам скидка N%»
const STORAGE_KEY = 'bina:referral';

interface ReferralState {
  /** Уже отправленный код (ref_…) */
  code: string;
  /** Скидка на первый Premium, %; 0 — не положена */
  discount: number;
  /** Плашку закрыли или скидка больше не действует */
  hidden: boolean;
}

function parse(raw: string | null): ReferralState | null {
  if (!raw) return null;
  try {
    const value: unknown = JSON.parse(raw);
    if (typeof value !== 'object' || value === null) return null;
    const { code, discount, hidden } = value as Record<string, unknown>;
    if (typeof code !== 'string' || typeof discount !== 'number') return null;
    return { code, discount, hidden: hidden === true };
  } catch {
    return null;
  }
}

function load(): ReferralState | null {
  try {
    return parse(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    return null;
  }
}

let state = load();
const listeners = new Set<() => void>();
/** Запрос уже в пути: эффект в StrictMode срабатывает дважды */
let applying = false;

function save(next: ReferralState): void {
  state = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Не сохранилось — при следующем запуске код уйдёт ещё раз, бэкенд это переживёт
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): ReferralState | null {
  return state;
}

/** Скидка уже не нужна (Premium оплачен или бэкенд её не даёт) — плашку больше не показываем */
export function hideReferralBanner(): void {
  if (state && !state.hidden) save({ ...state, hidden: true });
}

/** Отправить код друга при запуске по ссылке startapp=ref_<код>; вызывается один раз в Layout */
export function useReferralApply(): void {
  const { user } = useAuth();
  // Только вход через Telegram: ссылка друга открывает мини-апп в Telegram
  const signedIn = user !== null && usesServerFavorites();

  useEffect(() => {
    const code = referralStartCode(getStartParam());
    if (!signedIn || !code || state?.code === code || applying) return;
    applying = true;
    const body: ReferralApplyRequest = { code };
    apiPost<ReferralApplyResponse>(REFERRAL_APPLY_API, body)
      .then(
        ({ discount_percent }) =>
          save({ code, discount: discount_percent, hidden: discount_percent <= 0 }),
        (error: unknown) => {
          // Неверный код — больше не пробуем; сеть или сервер — попробуем при следующем запуске
          const status = error instanceof ApiError ? error.status : 0;
          if (status >= 400 && status < 500 && status !== 401) {
            save({ code, discount: 0, hidden: true });
          }
        },
      )
      .finally(() => {
        applying = false;
      });
  }, [signedIn]);
}

/** Плашка «Вам скидка N% на первый Premium»: discount > 0 — показать */
export function useReferralBanner() {
  const current = useSyncExternalStore(subscribe, getSnapshot);
  const discount = current && !current.hidden ? current.discount : 0;
  const hide = useCallback(() => hideReferralBanner(), []);
  return { discount, hide };
}
