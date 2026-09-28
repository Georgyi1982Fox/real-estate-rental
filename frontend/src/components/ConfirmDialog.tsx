import { useI18n } from '../providers/I18nProvider';
import Modal from './Modal';

export const DIALOG_BUTTON_CLASS =
  'inline-flex min-h-11 flex-1 items-center justify-center rounded-[var(--radius-md)] px-4 py-2.5 text-sm font-semibold active:scale-[.98] disabled:opacity-60';
export const DIALOG_CANCEL_CLASS = `${DIALOG_BUTTON_CLASS} border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--surface-hover)]`;

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  text: string;
  confirmLabel: string;
  /** Опасное действие (удаление) — красная кнопка */
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

/** Подтверждение действия в модалке: «Отмена» и кнопка действия */
export default function ConfirmDialog({
  open,
  title,
  text,
  confirmLabel,
  danger = false,
  busy = false,
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  const { t } = useI18n();

  return (
    <Modal open={open} title={title} onClose={onClose}>
      <p className="confirm-dialog__text text-sm leading-relaxed text-[var(--text-secondary)]">
        {text}
      </p>
      <footer className="confirm-dialog__actions mt-6 flex gap-3">
        <button type="button" className={DIALOG_CANCEL_CLASS} onClick={onClose}>
          {t.common.cancel}
        </button>
        <button
          type="button"
          className={`${DIALOG_BUTTON_CLASS} text-white ${danger ? 'bg-[var(--danger)] hover:opacity-90' : 'bg-[var(--primary)] hover:bg-[var(--primary-hover)]'}`}
          disabled={busy}
          aria-busy={busy}
          onClick={onConfirm}
        >
          {confirmLabel}
        </button>
      </footer>
    </Modal>
  );
}
