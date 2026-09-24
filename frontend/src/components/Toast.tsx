export type ToastType = 'success' | 'error' | 'info';

const TYPE_CLASS: Record<ToastType, string> = {
  success: 'border-[var(--secondary)] text-[var(--secondary)]',
  error: 'border-[var(--danger)] text-[var(--danger)]',
  info: 'border-[var(--border)] text-[var(--text-primary)]',
};

interface ToastProps {
  message: string;
  type: ToastType;
}

export default function Toast({ message, type }: ToastProps) {
  return (
    <p
      role="status"
      className={`toast toast--${type} pointer-events-auto mb-2 rounded-[var(--radius-md)] border bg-[var(--surface)] px-4 py-3 text-sm font-medium shadow-[var(--shadow-lg)] ${TYPE_CLASS[type]}`}
    >
      {message}
    </p>
  );
}
