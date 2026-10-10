import { useId, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, apiPost } from '../api/client';
import type { ComplaintReason, ComplaintRequest } from '../api/types';
import { useApi } from '../hooks/useApi';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import { DIALOG_BUTTON_CLASS, DIALOG_CANCEL_CLASS } from './ConfirmDialog';
import ErrorState from './ErrorState';
import Modal from './Modal';
import OpenInTelegram from './OpenInTelegram';

const COMMENT_MAX_LENGTH = 500;

interface ComplaintModalProps {
  open: boolean;
  onClose: () => void;
  /** Куда отправить жалобу: /api/hotels/{id}/complaints, /api/listings/{id}/complaints */
  path: string;
}

/**
 * «Пожаловаться»: причина из GET /api/complaints/reasons (названия уже на языке
 * пользователя) и необязательный комментарий. Гостю (401) — предложение войти.
 * Ответ 429 — больше 20 жалоб за сутки
 */
export default function ComplaintModal({ open, onClose, path }: ComplaintModalProps) {
  const { lang, t } = useI18n();
  const ct = t.complaint;
  const showToast = useToast();
  const commentId = useId();
  // lang в адресе: при смене языка причины запрашиваются заново
  const reasons = useApi<ComplaintReason[]>(open ? `/api/complaints/reasons?lang=${lang}` : null);
  const [reason, setReason] = useState('');
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [loginAsked, setLoginAsked] = useState(false);
  const [wasOpen, setWasOpen] = useState(open);

  // Каждое открытие — с чистой формы
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) {
      setReason('');
      setComment('');
      setLoginAsked(false);
    }
  }

  // Причины и сама жалоба — только после входа
  const needLogin = loginAsked || reasons.error?.isUnauthorized === true;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!reason || busy) return;
    setBusy(true);
    try {
      const body: ComplaintRequest = { reason, comment: comment.trim() };
      await apiPost<unknown>(path, body);
      haptic('success');
      showToast(ct.sent, 'success');
      onClose();
    } catch (error) {
      if (error instanceof ApiError && error.isUnauthorized) {
        setLoginAsked(true);
        return;
      }
      haptic('error');
      showToast(ct.error, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} title={needLogin ? ct.login : ct.title} onClose={onClose}>
      {needLogin ? (
        <OpenInTelegram plain />
      ) : (
        <form className="complaint flex flex-col gap-4" onSubmit={(event) => void handleSubmit(event)}>
          {reasons.loading && (
            <p className="m-0 flex justify-center py-6">
              <span className="spinner" aria-hidden="true" />
            </p>
          )}
          {reasons.error && <ErrorState compact onRetry={reasons.reload} />}

          {reasons.data && (
            <fieldset className="complaint__reasons m-0 min-w-0 border-0 p-0">
              <legend className="mb-2 p-0 text-sm font-semibold">{ct.reason}</legend>
              <ul className="m-0 flex list-none flex-col gap-1 p-0">
                {reasons.data.map((item) => (
                  <li key={item.code}>
                    <label className="complaint__reason flex min-h-11 cursor-pointer items-center gap-3 rounded-[var(--radius-md)] px-3 py-2 text-sm hover:bg-[var(--surface-hover)] has-[:checked]:bg-[var(--surface-hover)] has-[:checked]:font-semibold">
                      <input
                        type="radio"
                        name="reason"
                        value={item.code}
                        checked={reason === item.code}
                        className="size-4 shrink-0 accent-[var(--primary)]"
                        onChange={() => {
                          haptic('selection');
                          setReason(item.code);
                        }}
                      />
                      <span className="min-w-0 break-words">{item.title}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </fieldset>
          )}

          {reasons.data && (
            <p className="complaint__comment m-0 flex flex-col gap-1.5">
              <label htmlFor={commentId} className="text-sm font-semibold">
                {ct.comment}
              </label>
              <textarea
                id={commentId}
                name="comment"
                rows={3}
                maxLength={COMMENT_MAX_LENGTH}
                value={comment}
                className="w-full resize-y rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2.5 text-base text-[var(--text-primary)]"
                onChange={(event) => setComment(event.target.value)}
              />
            </p>
          )}

          <footer className="complaint__actions flex gap-3">
            <button type="button" className={DIALOG_CANCEL_CLASS} onClick={onClose}>
              {t.common.cancel}
            </button>
            <button
              type="submit"
              className={`${DIALOG_BUTTON_CLASS} bg-[var(--danger)] text-white hover:opacity-90`}
              disabled={!reason || busy}
              aria-busy={busy}
            >
              {ct.send}
            </button>
          </footer>
        </form>
      )}
    </Modal>
  );
}
