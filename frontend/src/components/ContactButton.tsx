interface ContactButtonProps {
  /** «Написать» или, у объявления хозяина, «Написать хозяину» */
  label: string;
  onClick: () => void;
  loading: boolean;
}

/** Кнопка «Написать» для браузера; внутри Telegram её заменяет MainButton (логика — useContact) */
export default function ContactButton({ label, onClick, loading }: ContactButtonProps) {
  return (
    <button
      type="button"
      className="listing-contact__write inline-flex min-h-12 items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-4 py-3 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98] disabled:opacity-70"
      disabled={loading}
      aria-busy={loading}
      onClick={onClick}
    >
      {loading ? (
        <span className="spinner" aria-hidden="true" />
      ) : (
        <span aria-hidden="true">💬</span>
      )}
      {label}
    </button>
  );
}
