import type { AcceptanceOption } from '../api/types';
import { ACCEPTANCE_COMMENT_MAX, STATUS_DEFECT, STATUS_OK } from '../lib/acceptance';
import type { AcceptanceMark } from '../lib/acceptance';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { FIELD_INPUT_CLASS, fieldBorderClass } from './FormField';

const STATUS_CLASS =
  'acceptance-item__status inline-flex min-h-11 min-w-0 items-center justify-center rounded-[var(--radius-md)] border px-1.5 py-2 text-center text-[13px] font-medium leading-tight break-words transition-colors duration-200 active:scale-[.97]';

/** Цвет выбранного состояния: в порядке — зелёный, дефект — жёлтый, остальное — красный */
function statusClass(code: string, selected: boolean): string {
  if (!selected) {
    return 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--surface-hover)]';
  }
  if (code === STATUS_OK) {
    return 'border-[var(--success-text)] bg-[var(--success-bg)] text-[var(--success-text)]';
  }
  if (code === STATUS_DEFECT) {
    return 'border-[var(--warning-border)] bg-[var(--warning-bg)] text-[var(--warning-text)]';
  }
  return 'border-[var(--danger-border)] bg-[var(--danger-bg)] text-[var(--danger-text)]';
}

interface AcceptanceItemRowProps {
  item: AcceptanceOption;
  /** Состояния с названиями — из чек-листа бэкенда */
  statuses: AcceptanceOption[];
  mark: AcceptanceMark | undefined;
  /** Нажали на состояние: поставить его или снять, если оно уже выбрано */
  onStatus: (status: string) => void;
  onComment: (comment: string) => void;
}

/** Пункт чек-листа: три кнопки состояния и комментарий, если выбран «Дефект» */
export default function AcceptanceItemRow({
  item,
  statuses,
  mark,
  onStatus,
  onComment,
}: AcceptanceItemRowProps) {
  const { t } = useI18n();
  const at = t.acceptance;

  return (
    <li className="acceptance-item flex flex-col gap-2 py-3">
      <fieldset className="acceptance-item__states m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
        <legend className="acceptance-item__title mb-2 p-0 text-sm font-medium break-words">
          {item.title}
        </legend>
        <div className="grid grid-cols-3 gap-2">
          {statuses.map((status) => {
            const selected = mark?.status === status.code;
            return (
              <button
                key={status.code}
                type="button"
                className={`${STATUS_CLASS} ${statusClass(status.code, selected)}`}
                aria-pressed={selected}
                onClick={() => {
                  haptic('selection');
                  onStatus(status.code);
                }}
              >
                {status.title}
              </button>
            );
          })}
        </div>
      </fieldset>
      {mark?.status === STATUS_DEFECT && (
        <input
          type="text"
          className={`${FIELD_INPUT_CLASS} acceptance-item__comment min-h-11 ${fieldBorderClass(false)}`}
          aria-label={`${at.comment}: ${item.title}`}
          placeholder={at.comment_placeholder}
          autoComplete="off"
          maxLength={ACCEPTANCE_COMMENT_MAX}
          value={mark.comment}
          onChange={(event) => onComment(event.target.value)}
        />
      )}
    </li>
  );
}
