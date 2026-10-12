import type { AssistantProblem, ViewingQuestions } from '../hooks/useAssistant';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import AssistantComposeButton from './AssistantComposeButton';

interface AssistantQuestionsProps {
  /** Последний составленный список и отмеченные в нём вопросы */
  saved: ViewingQuestions | undefined;
  busy: boolean;
  disabled: boolean;
  problem: AssistantProblem | null;
  onCompose: () => void;
  onToggle: (index: number) => void;
}

/** «Что спросить на просмотре»: вопросы от AI по этой квартире, заданные отмечаются галочкой */
export default function AssistantQuestions({
  saved,
  busy,
  disabled,
  problem,
  onCompose,
  onToggle,
}: AssistantQuestionsProps) {
  const { t } = useI18n();
  const at = t.listing.assistant;

  return (
    <section className="assistant-questions flex flex-col gap-3" aria-label={at.questions}>
      {saved && (
        <>
          <p className="assistant-questions__hint m-0 text-xs text-[var(--text-secondary)]">
            {at.questions_hint}
          </p>
          <ul
            className={`assistant-questions__list m-0 flex list-none flex-col gap-1 p-0 transition-opacity ${busy ? 'opacity-60' : ''}`}
          >
            {saved.items.map((question, index) => (
              <li key={`${index}-${question}`}>
                <label className="assistant-questions__item flex min-h-11 cursor-pointer items-start gap-3 rounded-[var(--radius-md)] px-3 py-2.5 text-sm leading-5 hover:bg-[var(--surface-hover)] has-[:checked]:text-[var(--text-secondary)] has-[:checked]:line-through">
                  <input
                    type="checkbox"
                    checked={saved.checked.includes(index)}
                    className="mt-0.5 size-4 shrink-0 accent-[var(--primary)]"
                    onChange={() => {
                      haptic('selection');
                      onToggle(index);
                    }}
                  />
                  <span className="min-w-0 break-words">{question}</span>
                </label>
              </li>
            ))}
          </ul>
        </>
      )}

      <AssistantComposeButton
        label={saved ? at.compose_again : at.compose}
        busy={busy}
        disabled={disabled}
        problem={problem}
        secondary={Boolean(saved)}
        onClick={onCompose}
      />
    </section>
  );
}
