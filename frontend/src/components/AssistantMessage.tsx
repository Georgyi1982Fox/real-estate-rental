import { useId } from 'react';
import type { FormEvent } from 'react';
import type { AssistantProblem, OwnerMessage } from '../hooks/useAssistant';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import AssistantComposeButton from './AssistantComposeButton';
import ExternalLink from './ExternalLink';
import Icon from './Icon';

/** Столько символов «о себе» принимает бэкенд */
const NOTE_MAX_LENGTH = 300;

const TEXT_CLASS =
  'm-0 select-text whitespace-pre-line break-words rounded-[var(--radius-md)] bg-[var(--surface-hover)] p-3 text-sm leading-relaxed text-[var(--text-primary)]';
const ACTION_CLASS =
  'inline-flex min-h-12 items-center justify-center gap-2 rounded-[var(--radius-md)] px-4 py-3 text-center text-sm font-semibold transition-colors active:scale-[.98]';

interface AssistantMessageProps {
  /** Последнее составленное сообщение */
  saved: OwnerMessage | undefined;
  busy: boolean;
  disabled: boolean;
  problem: AssistantProblem | null;
  /** «О себе» — что человек хочет сообщить хозяину; хранит родитель */
  note: string;
  onNoteChange: (note: string) => void;
  onCompose: () => void;
  /** Куда идти с готовым текстом: сайт-источник или переписка с хозяином в боте */
  openUrl: string;
  openLabel: string;
}

/**
 * «Написать хозяину»: AI составляет первое сообщение на грузинском и перевод.
 * Отправляет его человек сам — мы только даём скопировать текст и открыть объявление
 */
export default function AssistantMessage({
  saved,
  busy,
  disabled,
  problem,
  note,
  onNoteChange,
  onCompose,
  openUrl,
  openLabel,
}: AssistantMessageProps) {
  const { lang, t } = useI18n();
  const at = t.listing.assistant;
  const showToast = useToast();
  const noteId = useId();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onCompose();
  };

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      haptic('success');
      showToast(at.copied, 'success');
    } catch {
      // Буфер обмена недоступен (старый WebView, нет разрешения) — текст можно выделить рукой
      haptic('error');
      showToast(at.copy_error, 'error');
    }
  };

  // Грузинскому читателю перевод не нужен: это тот же текст
  const translation =
    saved && lang !== 'ka' && saved.translation.trim() !== saved.text_ka.trim()
      ? saved.translation.trim()
      : '';

  return (
    <form className="assistant-message flex flex-col gap-3" onSubmit={handleSubmit}>
      <p className="assistant-message__note m-0 flex flex-col gap-1.5">
        <label htmlFor={noteId} className="text-sm font-semibold">
          {at.note}
        </label>
        <textarea
          id={noteId}
          name="note"
          rows={2}
          maxLength={NOTE_MAX_LENGTH}
          value={note}
          placeholder={at.note_placeholder}
          disabled={busy}
          className="w-full resize-y rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2.5 text-base text-[var(--text-primary)] placeholder:text-[var(--text-secondary)] disabled:opacity-70"
          onChange={(event) => onNoteChange(event.target.value)}
        />
      </p>

      <AssistantComposeButton
        type="submit"
        label={saved ? at.compose_again : at.compose}
        busy={busy}
        disabled={disabled}
        problem={problem}
        secondary={Boolean(saved)}
      />

      {saved && (
        <section
          className={`assistant-message__result flex flex-col gap-3 transition-opacity ${busy ? 'opacity-60' : ''}`}
          aria-label={at.message}
        >
          <h3 className="assistant-message__label text-sm font-semibold">{at.text_ka}</h3>
          <p className={`assistant-message__text ${TEXT_CLASS}`} lang="ka">
            {saved.text_ka}
          </p>

          {translation && (
            <>
              <h3 className="assistant-message__label text-sm font-semibold">{at.translation}</h3>
              <p className={`assistant-message__translation ${TEXT_CLASS}`}>{translation}</p>
            </>
          )}

          <footer className="assistant-message__actions grid grid-cols-1 gap-2 sm:grid-cols-2">
            <button
              type="button"
              className={`${ACTION_CLASS} bg-[var(--primary)] text-white shadow-[var(--shadow-sm)] hover:bg-[var(--primary-hover)]`}
              onClick={() => void copy(saved.text_ka)}
            >
              <Icon name="copy" />
              {at.copy}
            </button>
            {openUrl && (
              <ExternalLink
                href={openUrl}
                className={`${ACTION_CLASS} border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--surface-hover)]`}
              >
                {openLabel} <span aria-hidden="true">↗</span>
              </ExternalLink>
            )}
          </footer>
          <p className="assistant-message__hint m-0 text-xs text-[var(--text-secondary)]">
            {at.send_hint}
          </p>
        </section>
      )}
    </form>
  );
}
