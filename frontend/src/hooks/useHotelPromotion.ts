import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, apiGet, apiPost } from '../api/client';
import type { HotelId, HotelPromotionInvoice, MyHotel } from '../api/types';
import { fillVars, formatDayMonth } from '../lib/format';
import { canPay, haptic, isInTelegram, openInvoice } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

// «Топ» включает бот после оплаты, это занимает пару секунд: после 'paid' перезапрашиваем
// объект, пока срок не изменится (паузы перед попытками)
const CONFIRM_DELAYS_MS = [1500, 2000, 3000];

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

/** «🔥 Топ» ещё действует */
export function isPromotedNow(hotel: Pick<MyHotel, 'promoted_until'>): boolean {
  const until = hotel.promoted_until ? new Date(hotel.promoted_until).getTime() : NaN;
  return Number.isFinite(until) && until > Date.now();
}

/**
 * Покупка «🔥 Топ» для своего объекта: счёт от бэкенда → окно оплаты Telegram → ждём,
 * пока бот поднимет объект. onUpdated получает объект с новым promoted_until
 */
export function useHotelPromotion(onUpdated: (hotel: MyHotel) => void) {
  const { lang, t } = useI18n();
  const mt = t.my_hotels;
  const showToast = useToast();
  const [payingId, setPayingId] = useState<HotelId | null>(null);
  // Страницу закрыли во время оплаты — дальше не опрашиваем сервер
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  /** Дождаться, пока бот продлит «Топ»: объект с новым сроком или null */
  const confirmPayment = useCallback(
    async (hotel: MyHotel): Promise<MyHotel | null> => {
      for (const delay of CONFIRM_DELAYS_MS) {
        await wait(delay);
        if (!alive.current) return null;
        try {
          const fresh = await apiGet<MyHotel>(`/api/my/hotels/${hotel.id}`);
          onUpdated(fresh);
          if (fresh.promoted_until && fresh.promoted_until !== hotel.promoted_until) return fresh;
        } catch {
          // Сеть мигнула — попробуем на следующем шаге
        }
      }
      return null;
    },
    [onUpdated],
  );

  const promote = useCallback(
    async (hotel: MyHotel) => {
      if (payingId !== null) return;
      // Окно оплаты звёздами есть только в Telegram
      if (!canPay()) {
        showToast(isInTelegram() ? t.premium.update_telegram : mt.top_telegram_only, 'info');
        return;
      }
      setPayingId(hotel.id);
      try {
        const { url } = await apiPost<HotelPromotionInvoice>(
          `/api/my/hotels/${hotel.id}/promotion`,
        );
        const status = await openInvoice(url);
        if (status === 'paid') {
          haptic('success');
          const fresh = await confirmPayment(hotel);
          if (!alive.current) return;
          const until = fresh?.promoted_until ? formatDayMonth(fresh.promoted_until, lang) : '';
          showToast(until ? fillVars(mt.top_done, { date: until }) : mt.top_activating, 'success');
        } else if (status === 'pending') {
          showToast(mt.top_pending, 'info');
        } else if (status === 'failed') {
          haptic('error');
          showToast(mt.top_failed, 'error');
        }
        // 'cancelled' — хозяин сам закрыл окно, ничего не показываем
      } catch (failure) {
        haptic('error');
        // 409: объект снят, скрыт или без номера с ценой
        const unlisted = failure instanceof ApiError && failure.status === 409;
        showToast(unlisted ? mt.top_unlisted : mt.top_error, 'error');
      } finally {
        if (alive.current) setPayingId(null);
      }
    },
    [payingId, confirmPayment, showToast, lang, mt, t.premium.update_telegram],
  );

  return { promote, payingId };
}
