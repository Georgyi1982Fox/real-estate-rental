import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import type { DocumentDelivery, Listing } from '../api/types';
import { useDocumentDelivery } from '../hooks/useDocumentDelivery';
import { BOT_URL } from '../lib/config';
import {
  CONTRACT_FIELDS,
  contractDraft,
  contractProblems,
  contractServerErrors,
  toContractRequest,
} from '../lib/contract';
import type { ContractDraft, ContractErrors, ContractField } from '../lib/contract';
import { fill } from '../lib/format';
import { submitDelivery } from '../lib/signing';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import ContractForm from './ContractForm';
import DocumentSent from './DocumentSent';
import ExternalLink from './ExternalLink';
import Icon from './Icon';
import Modal from './Modal';
import SigningSent from './SigningSent';

/** Что показать над кнопкой: ошибки в полях, бот не смог написать (502) или общий сбой */
type Problem = 'fix' | 'bot' | 'failed';

/** Документ на подписи: ссылка для второй стороны и прислал ли бот файл в чат */
interface Signing {
  inviteUrl: string;
  sent: boolean;
}

interface ContractModalProps {
  open: boolean;
  listing: Listing;
  onClose: () => void;
  /** Сервер не узнал пользователя (401): родитель покажет вход через Telegram */
  onLogin: () => void;
}

/**
 * Окно «Договор аренды» (только Premium): анкета → бот присылает двуязычный PDF в чат
 * или документ уходит на подпись обеим сторонам (FRONTEND-042).
 * Анкета живёт, пока открыта страница объявления: закрыли окно и вернулись — всё на месте
 */
export default function ContractModal({ open, listing, onClose, onLogin }: ContractModalProps) {
  const { lang, t } = useI18n();
  const ct = t.contract;
  const formId = useId();
  const showToast = useToast();
  const { busy, send } = useDocumentDelivery(
    `/api/listings/${encodeURIComponent(String(listing.id))}/contract`,
  );
  const [draft, setDraft] = useState<ContractDraft>(() => contractDraft(listing, lang));
  const [errors, setErrors] = useState<ContractErrors>({});
  const [problem, setProblem] = useState<Problem | null>(null);
  // Имя отправленного файла: вместо анкеты — экран «Договор отправлен»
  const [sent, setSent] = useState<string | null>(null);
  const [signing, setSigning] = useState<Signing | null>(null);
  // Кнопка, которой отправили анкету: на ней крутится индикатор
  const [mode, setMode] = useState<DocumentDelivery>('chat');
  const formRef = useRef<HTMLFormElement | null>(null);
  // Поле, к которому надо перейти (объект — чтобы повторная ошибка в том же поле сработала снова)
  const [focusOn, setFocusOn] = useState<{ field: ContractField } | null>(null);
  // Пока идёт отправка, поля выключены и фокус не примут — ждём её конца
  useEffect(() => {
    if (!focusOn || busy) return;
    const input = formRef.current?.elements.namedItem(focusOn.field);
    if (input instanceof HTMLElement) input.focus();
  }, [focusOn, busy]);
  // Окно могли закрыть, пока шёл запрос: тогда об итоге сообщает уведомление
  const openRef = useRef(open);
  useEffect(() => {
    openRef.current = open;
  }, [open]);

  const change = (patch: Partial<ContractDraft>) => {
    setDraft((current) => ({ ...current, ...patch }));
    // Поле исправляют — его ошибка больше не актуальна
    const fixed = (Object.keys(patch) as (keyof ContractDraft)[]).filter(
      (field): field is ContractField => field in errors,
    );
    if (fixed.length === 0) return;
    const rest = { ...errors };
    fixed.forEach((field) => delete rest[field]);
    setErrors(rest);
    if (Object.keys(rest).length === 0 && problem === 'fix') setProblem(null);
  };

  /** Подсветить поля и перейти к первому из них */
  const reject = (found: ContractErrors) => {
    haptic('error');
    setErrors(found);
    setProblem('fix');
    const first = CONTRACT_FIELDS.find((field) => found[field]);
    if (first) setFocusOn({ field: first });
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    formRef.current = event.currentTarget;
    const found = contractProblems(draft);
    if (Object.keys(found).length > 0) {
      reject(found);
      return;
    }
    const delivery = submitDelivery(event);
    haptic('light');
    setMode(delivery);
    setErrors({});
    setProblem(null);
    const result = await send(toContractRequest(draft, delivery));

    if (result.status === 'sent') {
      haptic('success');
      setSent(result.filename);
      if (!openRef.current) showToast(ct.sent_title, 'success');
    } else if (result.status === 'signing') {
      haptic('success');
      setSigning({ inviteUrl: result.inviteUrl, sent: result.sent });
      if (!openRef.current) showToast(t.signing.sent_title, 'success');
    } else if (result.status === 'login') {
      onClose();
      onLogin();
    } else if (result.status === 'premium') {
      // Окно «Подключить Premium» уже открыто — анкету убираем из-под него
      onClose();
    } else if (result.status === 'invalid') {
      const rejected = contractServerErrors(result.error);
      if (Object.keys(rejected).length > 0) reject(rejected);
      else setProblem('failed');
    } else if (result.status === 'bot' || result.status === 'failed') {
      haptic('error');
      setProblem(result.status);
      if (!openRef.current) showToast(ct.errors[result.status], 'error');
    }
  };

  const footer =
    sent || signing ? undefined : (
      <div className="contract-modal__footer flex flex-col gap-2">
        {problem && !busy && (
          <p
            className="contract-modal__problem m-0 text-center text-sm font-medium text-[var(--danger)]"
            role="alert"
          >
            {ct.errors[problem]}{' '}
            {problem === 'bot' && (
              <ExternalLink href={BOT_URL} className="underline underline-offset-2">
                {ct.open_bot} ↗
              </ExternalLink>
            )}
          </p>
        )}
        <button
          type="submit"
          form={formId}
          data-delivery="chat"
          className="contract-modal__submit inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-4 py-3 text-center text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98] disabled:opacity-70"
          disabled={busy}
          aria-busy={busy && mode === 'chat'}
        >
          {busy && mode === 'chat' ? (
            <span className="spinner" aria-hidden="true" />
          ) : (
            <Icon name="file" />
          )}
          {busy && mode === 'chat' ? ct.sending : ct.submit}
        </button>
        <button
          type="submit"
          form={formId}
          data-delivery="sign"
          className="contract-modal__sign inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-center text-sm font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-hover)] active:scale-[.98] disabled:opacity-70"
          disabled={busy}
          aria-busy={busy && mode === 'sign'}
        >
          {busy && mode === 'sign' ? (
            <span className="spinner" aria-hidden="true" />
          ) : (
            <Icon name="signature" />
          )}
          {busy && mode === 'sign' ? ct.sending : t.signing.sign_button}
        </button>
      </div>
    );

  return (
    <Modal open={open} title={ct.title} onClose={onClose} footer={footer}>
      {signing ? (
        <SigningSent
          inviteUrl={signing.inviteUrl}
          sent={signing.sent}
          editLabel={ct.edit}
          onEdit={() => setSigning(null)}
        />
      ) : sent ? (
        <DocumentSent
          title={ct.sent_title}
          text={fill(ct.sent_text, sent)}
          editLabel={ct.edit}
          onEdit={() => setSent(null)}
        />
      ) : (
        <ContractForm
          id={formId}
          draft={draft}
          errors={errors}
          disabled={busy}
          onChange={change}
          onSubmit={(event) => void submit(event)}
        />
      )}
    </Modal>
  );
}
