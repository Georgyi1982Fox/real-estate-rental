import { Link } from 'react-router-dom';
import { useCompare } from '../hooks/useCompare';
import { COMPARE_MIN, COMPARE_PATH } from '../lib/compare';
import { fill } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

/**
 * Плашка внизу экрана (над нижней панелью), пока что-то отмечено для сравнения:
 * «⚖ Сравнить (2)» → экран сравнения. С одной квартирой — подсказка выбрать ещё одну.
 * Отступ снизу (над панелью вкладок) — в main.css (.compare-bar)
 */
export default function CompareBar() {
  const { t } = useI18n();
  const ct = t.compare;
  const { count, clear } = useCompare();

  if (count === 0) return null;

  const ready = count >= COMPARE_MIN;

  return (
    <>
      {/* Последние карточки не прячутся под плашкой */}
      <div className="compare-bar__spacer h-20" aria-hidden="true" />
      <aside
        className="compare-bar fixed inset-x-0 z-30 px-4 pb-2 pl-[calc(1rem+var(--safe-left))] pr-[calc(1rem+var(--safe-right))]"
        aria-label={ct.bar_label}
      >
        <div className="compare-bar__body mx-auto flex max-w-md items-center gap-2 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-2 shadow-[var(--shadow-lg)]">
          {ready ? (
            <Link
              to={COMPARE_PATH}
              className="compare-bar__open inline-flex min-h-12 min-w-0 flex-1 items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]"
              onClick={() => haptic('light')}
            >
              <Icon name="scale" className="size-5" />
              <span className="truncate">{fill(ct.bar_open, count)}</span>
            </Link>
          ) : (
            <p
              className="compare-bar__hint m-0 flex min-h-12 min-w-0 flex-1 items-center gap-2 px-2 text-sm font-medium text-[var(--text-secondary)]"
              role="status"
            >
              <Icon name="scale" className="size-5 text-[var(--text-primary)]" />
              <span className="min-w-0">{ct.bar_more}</span>
            </p>
          )}
          <button
            type="button"
            className="compare-bar__clear inline-flex size-12 shrink-0 items-center justify-center rounded-[var(--radius-md)] text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] active:scale-[.97]"
            aria-label={ct.bar_clear}
            title={ct.bar_clear}
            onClick={clear}
          >
            <Icon name="close" className="size-5" />
          </button>
        </div>
      </aside>
    </>
  );
}
