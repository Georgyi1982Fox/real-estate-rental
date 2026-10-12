import { useCallback, useId, useState } from 'react';
import { ApiError, apiGet } from '../api/client';
import type { AssistantAction, ListResponse, Listing, ListingId } from '../api/types';
import { useAssistant } from '../hooks/useAssistant';
import type { AssistantProblem } from '../hooks/useAssistant';
import type { DistrictNames } from '../hooks/useDistricts';
import { showPremiumPrompt } from '../hooks/usePremiumPrompt';
import { fill } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import AssistantCheaper from './AssistantCheaper';
import AssistantMessage from './AssistantMessage';
import AssistantQuestions from './AssistantQuestions';
import Icon from './Icon';
import type { IconName } from './Icon';
import Modal from './Modal';
import OpenInTelegram from './OpenInTelegram';
import PremiumBadge from './PremiumBadge';

type Tab = AssistantAction | 'cheaper';

type CheaperState =
  { status: 'idle' | 'loading' | 'failed' } | { status: 'done'; items: Listing[] };

const TABS: { id: Tab; icon: IconName }[] = [
  { id: 'message_owner', icon: 'message' },
  { id: 'viewing_questions', icon: 'list_checks' },
  { id: 'cheaper', icon: 'trending_down' },
];

interface ListingAssistantProps {
  listingId: ListingId;
  /** Куда идти с готовым сообщением: сайт-источник или переписка с хозяином в боте */
  openUrl: string;
  openLabel: string;
  districtNames: DistrictNames;
}

/**
 * «AI-помощник» на странице объявления (только Premium): сообщение хозяину на грузинском,
 * вопросы для просмотра и похожие квартиры дешевле. Блок видят все: без входа (401) —
 * окно входа через Telegram, без Premium (402) — общее окно «Подключить Premium».
 */
export default function ListingAssistant({
  listingId,
  openUrl,
  openLabel,
  districtNames,
}: ListingAssistantProps) {
  const { t } = useI18n();
  const at = t.listing.assistant;
  const panelId = useId();
  const assistant = useAssistant(listingId);
  const [tab, setTab] = useState<Tab | null>(null);
  const [problem, setProblem] = useState<{
    action: AssistantAction;
    kind: AssistantProblem;
  } | null>(null);
  // «О себе» живёт здесь: переключили вкладку и вернулись — набранный текст на месте
  const [note, setNote] = useState(assistant.message?.note ?? '');
  const [cheaper, setCheaper] = useState<CheaperState>({ status: 'idle' });
  const [loginOpen, setLoginOpen] = useState(false);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeLogin = useCallback(() => setLoginOpen(false), []);

  const labels: Record<Tab, string> = {
    message_owner: at.message,
    viewing_questions: at.questions,
    cheaper: at.cheaper,
  };

  const compose = async (action: AssistantAction, about?: string) => {
    haptic('light');
    setProblem(null);
    const result = await assistant.ask(action, about);
    if (result === 'ok') haptic('success');
    else if (result === 'login') setLoginOpen(true);
    else if (result === 'limit' || result === 'failed') {
      haptic('error');
      setProblem({ action, kind: result });
    }
  };

  // «Похожие дешевле» — без AI и вне дневного лимита, поэтому грузятся сразу при открытии
  const loadCheaper = async () => {
    setCheaper({ status: 'loading' });
    try {
      const data = await apiGet<ListResponse<Listing>>(
        `/api/listings/${encodeURIComponent(String(listingId))}/cheaper`,
      );
      setCheaper({ status: 'done', items: data.items ?? [] });
    } catch (error) {
      const needLogin = error instanceof ApiError && error.isUnauthorized;
      const needPremium = error instanceof ApiError && error.isPaymentRequired;
      if (!needLogin && !needPremium) {
        setCheaper({ status: 'failed' });
        return;
      }
      // Показывать нечего: закрываем вкладку и зовём войти или подключить Premium
      setCheaper({ status: 'idle' });
      setTab(null);
      if (needLogin) setLoginOpen(true);
      else showPremiumPrompt('assistant');
    }
  };

  const toggle = (next: Tab) => {
    haptic('light');
    const opening = tab !== next;
    setTab(opening ? next : null);
    if (
      opening &&
      next === 'cheaper' &&
      cheaper.status !== 'done' &&
      cheaper.status !== 'loading'
    ) {
      void loadCheaper();
    }
  };

  const problemOf = (action: AssistantAction) => (problem?.action === action ? problem.kind : null);

  return (
    <section
      className="listing-assistant flex flex-col gap-4 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5"
      aria-labelledby="listing-assistant-title"
    >
      <header className="listing-assistant__header space-y-1">
        <h2
          id="listing-assistant-title"
          className="flex flex-wrap items-center gap-2 text-lg font-semibold"
        >
          <Icon name="sparkles" className="size-5 text-[var(--accent)]" />
          {at.title}
          <PremiumBadge />
        </h2>
        <p className="listing-assistant__intro text-sm text-[var(--text-secondary)]">{at.intro}</p>
      </header>

      <ul className="listing-assistant__actions m-0 grid list-none grid-cols-1 gap-2 p-0 sm:grid-cols-3">
        {TABS.map(({ id, icon }) => {
          const open = tab === id;
          return (
            <li key={id} className="min-w-0">
              <button
                type="button"
                className={`listing-assistant__action flex h-full min-h-12 w-full items-center gap-2 rounded-[var(--radius-md)] border px-3 py-2.5 text-left text-sm font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-hover)] active:scale-[.98] ${
                  open
                    ? 'border-[var(--primary)] bg-[var(--surface-hover)]'
                    : 'border-[var(--border)] bg-[var(--surface)]'
                }`}
                aria-expanded={open}
                aria-controls={open ? panelId : undefined}
                onClick={() => toggle(id)}
              >
                <Icon name={icon} className="size-5 text-[var(--text-secondary)]" />
                <span className="min-w-0 flex-1 break-words">{labels[id]}</span>
                {/* AI отвечает, а вкладку свернули — индикатор остаётся на кнопке */}
                {assistant.busy === id ? (
                  <span className="spinner" aria-hidden="true" />
                ) : (
                  <Icon
                    name="chevron"
                    className={`size-4 text-[var(--text-secondary)] transition-transform duration-200 ${open ? '-rotate-90' : 'rotate-90'}`}
                  />
                )}
              </button>
            </li>
          );
        })}
      </ul>

      {tab !== null && (
        <section id={panelId} className="listing-assistant__panel" aria-label={labels[tab]}>
          {tab === 'message_owner' && (
            <AssistantMessage
              saved={assistant.message}
              busy={assistant.busy === 'message_owner'}
              disabled={assistant.busy !== null}
              problem={problemOf('message_owner')}
              note={note}
              onNoteChange={setNote}
              onCompose={() => void compose('message_owner', note)}
              openUrl={openUrl}
              openLabel={openLabel}
            />
          )}
          {tab === 'viewing_questions' && (
            <AssistantQuestions
              saved={assistant.questions}
              busy={assistant.busy === 'viewing_questions'}
              disabled={assistant.busy !== null}
              problem={problemOf('viewing_questions')}
              onCompose={() => void compose('viewing_questions')}
              onToggle={assistant.toggleQuestion}
            />
          )}
          {tab === 'cheaper' && (
            <AssistantCheaper
              listings={cheaper.status === 'done' ? cheaper.items : undefined}
              loading={cheaper.status === 'loading'}
              failed={cheaper.status === 'failed'}
              onRetry={() => void loadCheaper()}
              districtNames={districtNames}
            />
          )}
        </section>
      )}

      {assistant.remaining !== null && (
        <p
          className="listing-assistant__remaining m-0 text-xs text-[var(--text-secondary)]"
          role="status"
        >
          {fill(at.remaining, assistant.remaining)}
        </p>
      )}

      <Modal open={loginOpen} title={at.title} onClose={closeLogin}>
        <OpenInTelegram plain />
      </Modal>
    </section>
  );
}
