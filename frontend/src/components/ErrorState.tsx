import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

interface ErrorStateProps {
  onRetry: () => void;
  /** Короткая плашка вместо большого блока — когда на странице всё же есть что показать */
  compact?: boolean;
  /** Свой текст ошибки вместо общего «Не удалось загрузить данные» */
  text?: string;
}

const RETRY_CLASS =
  'inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]';

export default function ErrorState({ onRetry, compact = false, text }: ErrorStateProps) {
  const { t } = useI18n();

  const retryButton = (
    <button
      type="button"
      className={`error-state__retry ${RETRY_CLASS}`}
      onClick={() => {
        haptic('light');
        onRetry();
      }}
    >
      ↻ {t.common.retry}
    </button>
  );

  if (compact) {
    return (
      <section
        className="error-state error-state--compact flex flex-col gap-3 rounded-[var(--radius-lg)] border border-dashed border-[var(--danger)]/40 p-4 sm:flex-row sm:items-center sm:justify-between"
        role="alert"
      >
        <p className="flex gap-2 text-sm text-[var(--text-primary)]">
          <span aria-hidden="true">⚠️</span>
          <span>{text ?? t.common.error_title}</span>
        </p>
        {retryButton}
      </section>
    );
  }

  return (
    <section
      className="error-state flex flex-col items-center gap-3 rounded-[var(--radius-lg)] border border-dashed border-[var(--danger)]/40 px-4 py-16 text-center"
      role="alert"
    >
      <span className="text-3xl" aria-hidden="true">
        ⚠️
      </span>
      <p className="text-sm font-medium text-[var(--text-primary)]">
        {text ?? t.common.error_title}
      </p>
      <p className="max-w-xs text-sm text-[var(--text-secondary)]">{t.common.error_text}</p>
      <span className="mt-1">{retryButton}</span>
    </section>
  );
}
