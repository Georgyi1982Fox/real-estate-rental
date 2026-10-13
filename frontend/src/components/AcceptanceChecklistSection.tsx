import { useId } from 'react';
import type { AcceptanceOption, AcceptanceSection } from '../api/types';
import { markSectionOk, markedCount, toggleMark } from '../lib/acceptance';
import type { AcceptanceDraft } from '../lib/acceptance';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import AcceptanceItemRow from './AcceptanceItemRow';
import Icon from './Icon';

interface AcceptanceChecklistSectionProps {
  section: AcceptanceSection;
  statuses: AcceptanceOption[];
  draft: AcceptanceDraft;
  onChange: (patch: Partial<AcceptanceDraft>) => void;
}

/**
 * Раздел чек-листа приёмки (комнаты, кухня…): пункты с кнопками состояния, счётчик отмеченных
 * и «Всё в порядке» — разом отмечает пункты, которые ещё не трогали
 */
export default function AcceptanceChecklistSection({
  section,
  statuses,
  draft,
  onChange,
}: AcceptanceChecklistSectionProps) {
  const { t } = useI18n();
  const titleId = useId();
  const marked = markedCount(section, draft);
  const complete = marked === section.items.length;

  return (
    <section
      className="acceptance-section rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] px-4 pt-4 pb-1 shadow-[var(--shadow-sm)]"
      aria-labelledby={titleId}
    >
      <header className="acceptance-section__header flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <h3 id={titleId} className="min-w-0 text-base font-semibold break-words">
          {section.title}{' '}
          <span className="text-sm font-medium text-[var(--text-secondary)] tabular-nums">
            {marked}/{section.items.length}
          </span>
        </h3>
        <button
          type="button"
          className="acceptance-section__all-ok inline-flex min-h-10 items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3.5 py-2 text-sm font-medium text-[var(--text-primary)] transition-colors duration-200 hover:bg-[var(--surface-hover)] active:scale-[.97] disabled:opacity-60"
          disabled={complete}
          onClick={() => {
            haptic('light');
            onChange({ items: markSectionOk(draft, section) });
          }}
        >
          <Icon name="check" className="size-4 text-[var(--success-text)]" />
          {t.acceptance.all_ok}
        </button>
      </header>

      <ul className="acceptance-section__items m-0 mt-2 list-none divide-y divide-[var(--border)] p-0">
        {section.items.map((item) => (
          <AcceptanceItemRow
            key={item.code}
            item={item}
            statuses={statuses}
            mark={draft.items[item.code]}
            onStatus={(status) => onChange({ items: toggleMark(draft, item.code, status) })}
            onComment={(comment) => {
              const mark = draft.items[item.code];
              if (mark) onChange({ items: { ...draft.items, [item.code]: { ...mark, comment } } });
            }}
          />
        ))}
      </ul>
    </section>
  );
}
