import type { AssistantProblem } from '../hooks/useAssistant';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

interface AssistantComposeButtonProps {
  /** «Составить» или «Составить заново» */
  label: string;
  /** AI сейчас отвечает именно на этот запрос */
  busy: boolean;
  /** AI занят другим запросом по этому объявлению */
  disabled: boolean;
  problem: AssistantProblem | null;
  /** Ответ уже есть: кнопка «заново» — второстепенная, чтобы не тратить лимит случайно */
  secondary?: boolean;
  type?: 'button' | 'submit';
  onClick?: () => void;
}

const PRIMARY_CLASS =
  'bg-[var(--primary)] text-white shadow-[var(--shadow-sm)] hover:bg-[var(--primary-hover)]';
const SECONDARY_CLASS =
  'border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--surface-hover)]';

/**
 * Кнопка запроса к AI-помощнику. Ответ идёт 5–20 секунд: пока ждём — индикатор и подсказка,
 * нажать второй раз нельзя. Под кнопкой — «лимит исчерпан» (429) или «не получилось» (502)
 */
export default function AssistantComposeButton({
  label,
  busy,
  disabled,
  problem,
  secondary = false,
  type = 'button',
  onClick,
}: AssistantComposeButtonProps) {
  const { t } = useI18n();
  const at = t.listing.assistant;

  return (
    <>
      <button
        type={type}
        className={`assistant-compose inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] px-4 py-3 text-center text-sm font-semibold transition-colors active:scale-[.98] disabled:opacity-70 ${secondary ? SECONDARY_CLASS : PRIMARY_CLASS}`}
        disabled={busy || disabled}
        aria-busy={busy}
        onClick={onClick}
      >
        {busy ? <span className="spinner" aria-hidden="true" /> : <Icon name="sparkles" />}
        {busy ? at.composing : label}
      </button>
      {busy && (
        <p
          className="assistant-compose__wait m-0 text-center text-xs text-[var(--text-secondary)]"
          role="status"
        >
          {at.wait}
        </p>
      )}
      {problem && !busy && (
        <p
          className="assistant-compose__problem m-0 text-center text-sm font-medium text-[var(--danger)]"
          role="alert"
        >
          {problem === 'limit' ? at.limit : at.failed}
        </p>
      )}
    </>
  );
}
