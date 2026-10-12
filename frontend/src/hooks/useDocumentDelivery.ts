import { useCallback, useRef, useState } from 'react';
import { ApiError, apiPost } from '../api/client';
import type { DocumentSent } from '../api/types';
import { showPremiumPrompt } from './usePremiumPrompt';

/**
 * Чем закончился запрос документа: sent — бот прислал PDF в чат; login — 401; premium — 402
 * (окно «Подключить Premium» уже показано); invalid — 422, сервер не принял поля;
 * bot — 502, бот не смог написать человеку (не запущен или заблокирован); failed — всё остальное
 */
export type DeliveryResult =
  | { status: 'sent'; filename: string }
  | { status: 'invalid'; error: ApiError }
  | { status: 'busy' | 'login' | 'premium' | 'bot' | 'failed' };

/**
 * Документ в чат с ботом (договор аренды, акт приёмки): POST с анкетой, в ответ — имя файла.
 * Пока идёт запрос, второй не отправляется
 */
export function useDocumentDelivery(path: string) {
  const [busy, setBusy] = useState(false);
  // Состояние обновится только на следующем рендере, а двойное нажатие приходит раньше
  const pending = useRef(false);

  const send = useCallback(
    async (body: unknown): Promise<DeliveryResult> => {
      if (pending.current) return { status: 'busy' };
      pending.current = true;
      setBusy(true);
      try {
        const data = await apiPost<DocumentSent>(path, body);
        return data.sent ? { status: 'sent', filename: data.filename } : { status: 'failed' };
      } catch (error) {
        if (!(error instanceof ApiError)) return { status: 'failed' };
        if (error.isUnauthorized) return { status: 'login' };
        if (error.isPaymentRequired) {
          showPremiumPrompt('documents');
          return { status: 'premium' };
        }
        if (error.status === 422) return { status: 'invalid', error };
        if (error.status === 502) return { status: 'bot' };
        // 503 — бот не настроен, 0 — нет сети
        return { status: 'failed' };
      } finally {
        pending.current = false;
        setBusy(false);
      }
    },
    [path],
  );

  return { busy, send };
}
