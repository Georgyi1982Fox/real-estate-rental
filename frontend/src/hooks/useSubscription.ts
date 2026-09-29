import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, apiGet, apiPost } from '../api/client';
import type { InvoiceRequest, InvoiceResponse, Subscription } from '../api/types';
import { haptic, openInvoice } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

const API_PATH = '/api/subscription';

// Подписку включает бот после оплаты, это занимает 1–2 секунды: после 'paid'
// перезапрашиваем /api/subscription, пока срок не изменится (паузы перед попытками)
const CONFIRM_DELAYS_MS = [0, 2000, 3000];

interface State {
  data?: Subscription;
  error?: ApiError;
  loading: boolean;
}

function toApiError(error: unknown): ApiError {
  return error instanceof ApiError ? error : new ApiError(0, String(error));
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

/**
 * Подписка текущего пользователя (/api/subscription) и покупка через Telegram.openInvoice.
 * Гостю запрос не отправляется — бэкенд всё равно ответит 401.
 */
export function useSubscription() {
  const { t } = useI18n();
  const pt = t.premium;
  const showToast = useToast();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [state, setState] = useState<State>({ loading: true });
  const [attempt, setAttempt] = useState(0);
  const [buying, setBuying] = useState(false);
  // Страницу закрыли во время оплаты — дальше не опрашиваем сервер
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    const controller = new AbortController();
    // Старые данные не прячем: «Повторить» не должен мигать скелетоном
    setState((current) => ({ ...current, loading: true, error: undefined }));
    apiGet<Subscription>(API_PATH, controller.signal).then(
      (data) => setState({ data, loading: false }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setState((current) => ({ ...current, loading: false, error: toApiError(error) }));
      },
    );
    return () => controller.abort();
  }, [isAuthenticated, attempt]);

  const reload = useCallback(() => setAttempt((value) => value + 1), []);

  /** Дождаться, пока бот включит подписку: true — срок обновился */
  const confirmPayment = useCallback(async (expiresBefore: string | null): Promise<boolean> => {
    for (const delay of CONFIRM_DELAYS_MS) {
      await wait(delay);
      if (!alive.current) return false;
      try {
        const data = await apiGet<Subscription>(API_PATH);
        setState({ data, loading: false });
        if (data.is_premium && data.expires_at !== expiresBefore) return true;
      } catch {
        // Сеть мигнула — попробуем на следующем шаге
      }
    }
    return false;
  }, []);

  /** Купить план: счёт от бэкенда → окно оплаты Telegram → ждём включения подписки */
  const buy = useCallback(
    async (planId: string) => {
      if (buying) return;
      setBuying(true);
      const expiresBefore = state.data?.expires_at ?? null;
      try {
        const body: InvoiceRequest = { plan: planId };
        const { url } = await apiPost<InvoiceResponse>(`${API_PATH}/invoice`, body);
        const status = await openInvoice(url);
        if (status === 'paid') {
          haptic('success');
          const confirmed = await confirmPayment(expiresBefore);
          if (alive.current) showToast(confirmed ? pt.paid : pt.activating, 'success');
        } else if (status === 'pending') {
          showToast(pt.pending, 'info');
        } else if (status === 'failed') {
          haptic('error');
          showToast(pt.failed, 'error');
        }
        // 'cancelled' — пользователь сам закрыл окно, ничего не показываем
      } catch {
        haptic('error');
        showToast(pt.invoice_error, 'error');
      } finally {
        if (alive.current) setBuying(false);
      }
    },
    [buying, state.data, confirmPayment, showToast, pt],
  );

  // Гость или 401 от бэкенда (вне Telegram initData нет) — нужен вход через Telegram
  const unauthorized = (!authLoading && !isAuthenticated) || Boolean(state.error?.isUnauthorized);

  return {
    subscription: state.data,
    loading: authLoading || (isAuthenticated && state.loading && !state.data),
    // Если данные уже есть, неудачный повторный запрос их не прячет
    error: unauthorized || state.data ? undefined : state.error,
    unauthorized,
    reload,
    buy,
    buying,
  };
}
