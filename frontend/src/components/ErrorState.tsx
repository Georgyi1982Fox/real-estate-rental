import { useI18n } from '../providers/I18nProvider';

interface ErrorStateProps {
  onRetry: () => void;
}

export default function ErrorState({ onRetry }: ErrorStateProps) {
  const { t } = useI18n();

  return (
    <section
      className="error-state flex flex-col items-center gap-3 rounded-[var(--radius-lg)] border border-dashed border-[var(--danger)]/40 px-4 py-16 text-center"
      role="alert"
    >
      <span className="text-3xl" aria-hidden="true">
        ⚠️
      </span>
      <p className="text-sm font-medium text-[var(--text-primary)]">{t.common.error_title}</p>
      <p className="max-w-xs text-sm text-[var(--text-secondary)]">{t.common.error_text}</p>
      <button
        type="button"
        className="mt-1 inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]"
        onClick={onRetry}
      >
        ↻ {t.common.retry}
      </button>
    </section>
  );
}
