import { useCallback, useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import type { AcceptanceChecklist, Listing, Subscription } from '../api/types';
import AcceptanceChecklistSection from '../components/AcceptanceChecklistSection';
import AcceptanceDetails from '../components/AcceptanceDetails';
import AcceptanceSkeleton from '../components/AcceptanceSkeleton';
import DocumentSent from '../components/DocumentSent';
import ErrorState from '../components/ErrorState';
import ExternalLink from '../components/ExternalLink';
import Icon from '../components/Icon';
import Modal from '../components/Modal';
import OpenInTelegram from '../components/OpenInTelegram';
import PremiumBadge from '../components/PremiumBadge';
import { useAcceptanceDraft } from '../hooks/useAcceptanceDraft';
import { useApi } from '../hooks/useApi';
import { useDocumentDelivery } from '../hooks/useDocumentDelivery';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import {
  ACCEPTANCE_FIELDS,
  ACCEPTANCE_LISTING_PARAM,
  acceptanceAddress,
  acceptanceDraftKey,
  acceptanceProblems,
  acceptanceServerErrors,
  checkedItems,
  toAcceptanceRequest,
} from '../lib/acceptance';
import type {
  AcceptanceDraft,
  AcceptanceErrors,
  AcceptanceField,
  AcceptanceProblem,
} from '../lib/acceptance';
import { BOT_URL } from '../lib/config';
import { fill, fillVars, tr } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';

/** Что показать над кнопкой: ошибки в полях, бот не смог написать (502) или общий сбой */
type Problem = 'fix' | 'bot' | 'failed';

const PAGE_CLASS = 'acceptance mx-auto flex w-full max-w-2xl flex-col gap-5 py-2 sm:py-4';
const CHECKLIST_PATH = '/api/documents/acceptance/checklist';

/**
 * «Акт приёмки квартиры» (PDF — только Premium): чек-лист по разделам, данные акта →
 * бот присылает двуязычный PDF в чат. Открывается из объявления (`?listing=`: адрес берётся
 * из него) и из профиля (адрес вводится вручную). Черновик хранится на устройстве
 */
export default function AcceptancePage() {
  const { lang, t } = useI18n();
  const at = t.acceptance;
  const ct = t.contract;
  const [params] = useSearchParams();
  const listingParam = params.get(ACCEPTANCE_LISTING_PARAM);
  const { user, loading: authLoading } = useAuth();
  // Тексты чек-листа — на языке из профиля; lang в адресе — чтобы после смены языка запросить заново
  const checklist = useApi<AcceptanceChecklist>(user ? `${CHECKLIST_PATH}?lang=${lang}` : null);
  const listing = useApi<Listing>(
    listingParam ? `/api/listings/${encodeURIComponent(listingParam)}` : null,
  );
  const subscription = useApi<Subscription>(user ? '/api/subscription' : null);
  const { draft, change, reset } = useAcceptanceDraft(acceptanceDraftKey(listingParam));
  const { busy, send } = useDocumentDelivery('/api/documents/acceptance');
  const [errors, setErrors] = useState<AcceptanceErrors>({});
  const [problem, setProblem] = useState<Problem | null>(null);
  // Имя отправленного файла: вместо акта — экран «Акт отправлен»
  const [sent, setSent] = useState<string | null>(null);
  const [clearOpen, setClearOpen] = useState(false);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeClear = useCallback(() => setClearOpen(false), []);
  const formRef = useRef<HTMLFormElement | null>(null);
  const checklistRef = useRef<HTMLHeadingElement | null>(null);
  // Поле, к которому надо перейти (объект — чтобы повторная ошибка в том же поле сработала снова)
  const [focusOn, setFocusOn] = useState<{ field: AcceptanceField } | null>(null);
  // Пока идёт отправка, поля выключены и фокус не примут — ждём её конца
  useEffect(() => {
    if (!focusOn || busy) return;
    if (focusOn.field === 'items') {
      checklistRef.current?.scrollIntoView({ block: 'start' });
      checklistRef.current?.focus({ preventScroll: true });
      return;
    }
    const input = formRef.current?.elements.namedItem(focusOn.field);
    if (input instanceof HTMLElement) input.focus();
  }, [focusOn, busy]);

  useDocumentTitle(`${at.title} — bina.ai`);
  useTelegramBackButton(listingParam ? `/listing/${encodeURIComponent(listingParam)}` : '/profile');

  // Объявление не нашлось — акт всё равно можно составить, адрес вводится вручную
  const listingId = listing.data ? String(listing.data.id) : undefined;
  const listingAddress = listing.data ? tr(listing.data.address, lang).trim() : '';

  if (authLoading || (user && checklist.loading)) {
    return (
      <section className={PAGE_CLASS} aria-busy="true">
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{at.title}</h1>
        <AcceptanceSkeleton />
      </section>
    );
  }
  // Гость или 401 от бэкенда (вне Telegram initData нет) — нужен Telegram
  if (!user || checklist.error?.isUnauthorized) {
    return (
      <section className="acceptance acceptance--guest mx-auto w-full max-w-md py-6">
        <OpenInTelegram />
      </section>
    );
  }
  if (!checklist.data) return <ErrorState onRetry={checklist.reload} />;

  const list = checklist.data;
  const { sections, statuses } = list;
  const total = sections.reduce((count, section) => count + section.items.length, 0);
  const marked = checkedItems(draft, list).length;
  const address = acceptanceAddress(draft, listingAddress);

  const update = (patch: Partial<AcceptanceDraft>) => {
    change(patch);
    // Поле исправляют — его ошибка больше не актуальна
    const fixed = (Object.keys(patch) as (keyof AcceptanceDraft)[]).filter(
      (field): field is AcceptanceField => field in errors,
    );
    if (fixed.length === 0) return;
    const rest = { ...errors };
    fixed.forEach((field) => delete rest[field]);
    setErrors(rest);
    if (Object.keys(rest).length === 0 && problem === 'fix') setProblem(null);
  };

  const errorText = (found: AcceptanceProblem) =>
    found === 'items' || found === 'keys' ? at.errors[found] : ct.errors[found];
  const fieldError = (field: AcceptanceField) => {
    const found = errors[field];
    return found ? errorText(found) : undefined;
  };

  /** Подсветить поля и перейти к первому из них */
  const reject = (found: AcceptanceErrors) => {
    haptic('error');
    setErrors(found);
    setProblem('fix');
    const first = ACCEPTANCE_FIELDS.find((field) => found[field]);
    if (first) setFocusOn({ field: first });
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    const found = acceptanceProblems(draft, list, listingAddress);
    if (Object.keys(found).length > 0) {
      reject(found);
      return;
    }
    haptic('light');
    setErrors({});
    setProblem(null);
    const result = await send(toAcceptanceRequest(draft, list, listingAddress, listingId));

    if (result.status === 'sent') {
      haptic('success');
      setSent(result.filename);
      window.scrollTo({ top: 0 });
    } else if (result.status === 'login') {
      // Сессия закончилась: повторный запрос чек-листа ответит 401 и покажет вход
      checklist.reload();
    } else if (result.status === 'invalid') {
      const rejected = acceptanceServerErrors(result.error);
      if (Object.keys(rejected).length > 0) reject(rejected);
      else setProblem('failed');
    } else if (result.status === 'bot' || result.status === 'failed') {
      haptic('error');
      setProblem(result.status);
    }
    // premium: окно «Подключить Premium» уже открыто, акт остаётся в черновике
  };

  if (sent) {
    return (
      <section className={PAGE_CLASS}>
        <DocumentSent
          title={at.sent_title}
          text={fill(at.sent_text, sent)}
          editLabel={at.edit}
          onEdit={() => setSent(null)}
        />
      </section>
    );
  }

  return (
    <section className={PAGE_CLASS} aria-labelledby="acceptance-title">
      <header className="acceptance__header flex flex-col gap-2">
        <h1
          id="acceptance-title"
          className="flex flex-wrap items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl"
        >
          {at.title}
          <PremiumBadge />
        </h1>
        <p className="acceptance__intro m-0 text-sm text-[var(--text-secondary)]">{at.intro}</p>
        {listing.data && (
          <p className="acceptance__listing m-0 text-sm break-words">
            <span className="text-[var(--text-secondary)]">{at.listing}: </span>
            <Link
              to={`/listing/${encodeURIComponent(String(listing.data.id))}`}
              className="font-medium underline underline-offset-2"
            >
              {tr(listing.data.title, lang)}
            </Link>
          </p>
        )}
      </header>

      {subscription.data && !subscription.data.is_premium && (
        <aside className="acceptance__premium flex flex-col gap-2 rounded-[var(--radius-lg)] border border-[var(--warning-border)] bg-[var(--warning-bg)] p-4 text-sm text-[var(--warning-text)]">
          <p className="m-0">{at.premium_note}</p>
          <Link
            to="/premium"
            className="inline-flex min-h-11 items-center gap-1.5 self-start font-semibold underline underline-offset-2"
            onClick={() => haptic('light')}
          >
            <Icon name="crown" className="size-4" />
            {t.premium.get_premium}
          </Link>
        </aside>
      )}

      <form
        ref={formRef}
        className="acceptance__form flex flex-col gap-4"
        noValidate
        onSubmit={(event) => void submit(event)}
      >
        <header className="acceptance__checklist-header flex flex-col gap-1">
          <h2
            ref={checklistRef}
            tabIndex={-1}
            className="scroll-mt-20 text-lg font-semibold outline-none"
          >
            {at.checklist}{' '}
            <span className="text-sm font-medium text-[var(--text-secondary)] tabular-nums">
              · {fillVars(at.progress, { n: marked, total })}
            </span>
          </h2>
          <p
            className={`m-0 text-xs ${errors.items ? 'font-medium text-[var(--danger)]' : 'text-[var(--text-secondary)]'}`}
            role={errors.items ? 'alert' : undefined}
          >
            {fieldError('items') ?? at.unmarked_hint}
          </p>
        </header>

        {/* Чек-лист не выключаем на время отправки целиком: fieldset сбросил бы фокус с кнопки */}
        {sections.map((section) => (
          <AcceptanceChecklistSection
            key={section.code}
            section={section}
            statuses={statuses}
            draft={draft}
            onChange={busy ? () => undefined : update}
          />
        ))}

        <h2 className="mt-2 text-lg font-semibold">{at.details}</h2>
        <AcceptanceDetails
          draft={draft}
          address={address}
          error={fieldError}
          disabled={busy}
          onChange={update}
        />

        <p className="acceptance__disclaimer m-0 rounded-[var(--radius-md)] bg-[var(--surface-hover)] p-3 text-xs leading-relaxed text-[var(--text-secondary)]">
          {at.disclaimer}
        </p>

        <footer className="acceptance__footer flex flex-col gap-2">
          {problem && !busy && (
            <p
              className="acceptance__problem m-0 text-center text-sm font-medium text-[var(--danger)]"
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
            className="acceptance__submit inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-4 py-3 text-center text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98] disabled:opacity-70"
            disabled={busy}
            aria-busy={busy}
          >
            {busy ? <span className="spinner" aria-hidden="true" /> : <Icon name="file" />}
            {busy ? ct.sending : at.submit}
          </button>
          <p className="m-0 text-center text-xs text-[var(--text-secondary)]">{at.saved_hint}</p>
          <button
            type="button"
            className="acceptance__clear inline-flex min-h-11 items-center justify-center gap-2 self-center rounded-[var(--radius-md)] px-4 py-2.5 text-sm font-semibold text-[var(--text-secondary)] transition-colors hover:text-[var(--danger)] disabled:opacity-60"
            disabled={busy}
            aria-haspopup="dialog"
            onClick={() => {
              haptic('light');
              setClearOpen(true);
            }}
          >
            <Icon name="trash" className="size-4" />
            {at.clear}
          </button>
        </footer>
      </form>

      <Modal
        open={clearOpen}
        title={at.clear_title}
        onClose={closeClear}
        footer={
          <div className="flex gap-3">
            <button
              type="button"
              className="inline-flex min-h-12 flex-1 items-center justify-center rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-hover)] active:scale-[.98]"
              onClick={closeClear}
            >
              {t.common.cancel}
            </button>
            <button
              type="button"
              className="inline-flex min-h-12 flex-1 items-center justify-center rounded-[var(--radius-md)] bg-[var(--danger)] px-4 py-3 text-sm font-semibold text-white transition-colors active:scale-[.98]"
              onClick={() => {
                haptic('medium');
                reset();
                setErrors({});
                setProblem(null);
                setClearOpen(false);
                window.scrollTo({ top: 0 });
              }}
            >
              {at.clear}
            </button>
          </div>
        }
      >
        <p className="m-0 text-sm text-[var(--text-secondary)]">{at.clear_text}</p>
      </Modal>
    </section>
  );
}
