import { useEffect, useId, useRef } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { useI18n } from '../providers/I18nProvider';

interface ModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}

/** Универсальная модалка: bottom sheet на мобильном, по центру от 640px. Escape и клик по фону закрывают */
export default function Modal({ open, title, onClose, children }: ModalProps) {
  const { t } = useI18n();
  const titleId = useId();
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    panelRef.current?.focus();

    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('keydown', handleKey);
      previousFocus?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <section
      className="modal fixed inset-0 z-40 grid place-items-end bg-black/40 p-0 backdrop-blur-sm sm:place-items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <article
        ref={panelRef}
        tabIndex={-1}
        className="modal__panel w-full max-w-lg rounded-t-[var(--radius-lg)] bg-[var(--surface)]/95 p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] shadow-[var(--shadow-lg)] outline-none backdrop-blur-md sm:rounded-[var(--radius-lg)] sm:pb-5"
      >
        <header className="modal__header mb-4 flex items-center justify-between gap-4">
          <h2 id={titleId} className="text-lg font-semibold">
            {title}
          </h2>
          <button type="button" className="app-icon-button" aria-label={t.common.close} onClick={onClose}>
            ×
          </button>
        </header>
        {children}
      </article>
    </section>,
    document.body,
  );
}
