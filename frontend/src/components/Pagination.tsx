import { fill } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

interface PaginationProps {
  current: number;
  total: number;
  onChange: (page: number) => void;
}

export default function Pagination({ current, total, onChange }: PaginationProps) {
  const { t } = useI18n();
  if (total <= 1) return null;

  return (
    <nav aria-label={t.home.pagination} className="pagination flex items-center justify-center gap-2 pt-2">
      {Array.from({ length: total }, (_, index) => index + 1).map((page) => {
        const active = page === current;
        return (
          <button
            key={page}
            type="button"
            aria-label={fill(t.home.page_n, page)}
            aria-current={active ? 'page' : undefined}
            className={`inline-flex min-h-10 min-w-10 items-center justify-center rounded-[var(--radius-md)] border text-sm font-medium transition-colors ${active ? 'border-[var(--primary)] bg-[var(--primary)] text-white' : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--surface-hover)]'}`}
            onClick={() => {
              if (active) return;
              haptic('selection');
              onChange(page);
            }}
          >
            {page}
          </button>
        );
      })}
    </nav>
  );
}
