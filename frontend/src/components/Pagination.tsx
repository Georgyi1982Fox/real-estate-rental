import { fill } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

interface PaginationProps {
  current: number;
  total: number;
  onChange: (page: number) => void;
}

/** Сколько номеров страниц видно одновременно (окно сдвигается вместе с текущей) */
const WINDOW = 5;

// Подписи только этого компонента (здесь, а не в strings.ts — чтобы не пересекаться
// с параллельными правками словаря)
const LABELS = {
  ka: { prev: 'წინა გვერდი', next: 'შემდეგი გვერდი', of: 'გვერდი {n} / {total}' },
  ru: { prev: 'Предыдущая страница', next: 'Следующая страница', of: 'Страница {n} из {total}' },
  en: { prev: 'Previous page', next: 'Next page', of: 'Page {n} of {total}' },
} as const;

const BUTTON_CLASS =
  'inline-flex min-h-10 min-w-10 items-center justify-center rounded-[var(--radius-md)] border text-sm font-medium transition-colors';
const IDLE_CLASS =
  'border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--surface-hover)]';
const ACTIVE_CLASS = 'border-[var(--primary)] bg-[var(--primary)] text-white';
const DISABLED_CLASS =
  'border-[var(--border)] bg-[var(--surface)] text-[var(--text-secondary)] opacity-40';

/** Номера страниц в окне вокруг текущей: 1 2 [3] 4 5 … или … 4 5 [6] 7 8 … */
export function pageWindow(current: number, total: number, size = WINDOW): number[] {
  const count = Math.min(size, total);
  const start = Math.min(Math.max(1, current - Math.floor(count / 2)), total - count + 1);
  return Array.from({ length: count }, (_, index) => start + index);
}

export default function Pagination({ current, total, onChange }: PaginationProps) {
  const { lang, t } = useI18n();
  if (total <= 1) return null;
  const labels = LABELS[lang] ?? LABELS.ru;

  const go = (page: number) => {
    if (page < 1 || page > total || page === current) return;
    haptic('selection');
    onChange(page);
  };

  const arrow = (page: number, label: string, symbol: string) => {
    const disabled = page < 1 || page > total;
    return (
      <button
        type="button"
        aria-label={label}
        disabled={disabled}
        className={`${BUTTON_CLASS} ${disabled ? DISABLED_CLASS : IDLE_CLASS}`}
        onClick={() => go(page)}
      >
        <span aria-hidden="true">{symbol}</span>
      </button>
    );
  };

  return (
    <nav aria-label={t.home.pagination} className="pagination flex flex-col items-center gap-2 pt-2">
      <div className="flex items-center justify-center gap-2">
        {arrow(current - 1, labels.prev, '‹')}
        {pageWindow(current, total).map((page) => {
          const active = page === current;
          return (
            <button
              key={page}
              type="button"
              aria-label={fill(t.home.page_n, page)}
              aria-current={active ? 'page' : undefined}
              className={`${BUTTON_CLASS} ${active ? ACTIVE_CLASS : IDLE_CLASS}`}
              onClick={() => go(page)}
            >
              {page}
            </button>
          );
        })}
        {arrow(current + 1, labels.next, '›')}
      </div>
      <p className="pagination__status m-0 text-xs text-[var(--text-secondary)]">
        {labels.of.replace('{n}', String(current)).replace('{total}', String(total))}
      </p>
    </nav>
  );
}
