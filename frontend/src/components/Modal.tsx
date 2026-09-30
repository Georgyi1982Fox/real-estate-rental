import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import type { PointerEvent, ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { useTelegramBack } from '../hooks/useTelegramBackButton';
import { useI18n } from '../providers/I18nProvider';

/** Столько длится анимация закрытия в main.css (.modal[data-state='closing']) */
const CLOSE_MS = 200;
/** Лист закрывается, если его утянули вниз дальше этого или смахнули быстрее SWIPE_SPEED */
const SWIPE_DISTANCE = 96;
const SWIPE_SPEED = 0.5; // px/мс
/** Совпадает с брейкпоинтом sm: ниже — лист снизу, выше — окно по центру */
const SHEET_QUERY = '(max-width: 639.98px)';

// Прокрутку страницы под модалкой блокирует класс на <html>; счётчик — на случай двух модалок
let scrollLocks = 0;

function lockScroll(): () => void {
  if (scrollLocks++ === 0) document.documentElement.classList.add('scroll-locked');
  return () => {
    if (--scrollLocks === 0) document.documentElement.classList.remove('scroll-locked');
  };
}

interface Drag {
  pointerId: number;
  startY: number;
  startTime: number;
  offset: number;
}

interface ModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** Закреплённые внизу кнопки: контент прокручивается, футер остаётся на месте */
  footer?: ReactNode;
}

/**
 * Универсальная модалка: bottom sheet на мобильном, по центру от 640px.
 * Закрывается ✕, кликом по фону, Escape, свайпом вниз и кнопкой «Назад» Telegram.
 * Открытие и закрытие анимированы, страница под модалкой не прокручивается.
 */
export default function Modal({ open, title, onClose, children, footer }: ModalProps) {
  const { t } = useI18n();
  const titleId = useId();
  const panelRef = useRef<HTMLElement>(null);
  const dragRef = useRef<Drag | null>(null);
  // Пока идёт анимация закрытия, модалка ещё в DOM
  const [mounted, setMounted] = useState(open);
  if (open && !mounted) setMounted(true);
  const closing = mounted && !open;

  // Во время закрытия показываем то, что было открыто: родитель мог уже очистить данные
  const content = useRef({ title, children, footer });
  useLayoutEffect(() => {
    if (open) content.current = { title, children, footer };
  });
  const shown = open ? { title, children, footer } : content.current;

  useEffect(() => {
    if (!closing) return;
    const timer = window.setTimeout(() => setMounted(false), CLOSE_MS);
    return () => window.clearTimeout(timer);
  }, [closing]);

  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    panelRef.current?.focus();
    const unlock = lockScroll();

    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('keydown', handleKey);
      unlock();
      previousFocus?.focus();
    };
  }, [open, onClose]);

  useTelegramBack(onClose, open, 1);

  // Свайп вниз за шапку листа. Смещение — CSS-переменная, анимацию и переходы делает main.css
  const setOffset = (offset: number) => {
    panelRef.current?.style.setProperty('--sheet-drag', `${offset}px`);
  };

  const startDrag = (event: PointerEvent<HTMLElement>) => {
    if (!open || !event.isPrimary || event.button !== 0) return;
    if (!window.matchMedia(SHEET_QUERY).matches) return;
    // Кнопка ✕ в шапке должна нажиматься, а не тянуть лист
    if ((event.target as HTMLElement).closest('button')) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      startY: event.clientY,
      startTime: event.timeStamp,
      offset: 0,
    };
    panelRef.current?.classList.add('is-dragging');
  };

  const moveDrag = (event: PointerEvent<HTMLElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    drag.offset = Math.max(0, event.clientY - drag.startY);
    setOffset(drag.offset);
  };

  const endDrag = (event: PointerEvent<HTMLElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    dragRef.current = null;
    panelRef.current?.classList.remove('is-dragging');
    const speed = drag.offset / Math.max(1, event.timeStamp - drag.startTime);
    const dismissed =
      event.type === 'pointerup' && (drag.offset > SWIPE_DISTANCE || speed > SWIPE_SPEED);
    // Закрытие продолжает движение с текущего места; иначе лист возвращается на место
    if (dismissed) onClose();
    else setOffset(0);
  };

  if (!mounted) return null;

  return createPortal(
    <section
      className="modal fixed inset-0 z-40 grid place-items-end p-0 sm:place-items-center sm:p-4"
      data-state={closing ? 'closing' : 'open'}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onClick={(event) => {
        if (event.target === event.currentTarget && open) onClose();
      }}
    >
      <article
        ref={panelRef}
        tabIndex={-1}
        className="modal__panel relative flex max-h-[calc(100dvh-var(--safe-top)-1rem)] w-full max-w-lg flex-col rounded-t-[var(--radius-lg)] bg-[var(--surface)]/95 shadow-[var(--shadow-lg)] outline-none backdrop-blur-md sm:max-h-[calc(100dvh-2rem)] sm:rounded-[var(--radius-lg)]"
      >
        <header
          className="modal__header shrink-0 touch-none px-5 pb-4 pt-2 sm:touch-auto sm:pt-5"
          onPointerDown={startDrag}
          onPointerMove={moveDrag}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
        >
          <span
            className="modal__handle mx-auto mb-2 block h-1 w-10 rounded-full bg-[var(--border)] sm:hidden"
            aria-hidden="true"
          />
          <div className="flex items-center justify-between gap-4">
            <h2 id={titleId} className="text-lg font-semibold">
              {shown.title}
            </h2>
            <button
              type="button"
              className="app-icon-button"
              aria-label={t.common.close}
              onClick={onClose}
            >
              ×
            </button>
          </div>
        </header>
        <div
          className={`modal__body min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 ${
            shown.footer ? 'pb-5' : 'pb-[calc(1.25rem+var(--safe-bottom))] sm:pb-5'
          }`}
        >
          {shown.children}
        </div>
        {shown.footer && (
          <footer className="modal__footer shrink-0 border-t border-[var(--border)] px-5 pb-[calc(0.75rem+var(--safe-bottom))] pt-3 sm:pb-4">
            {shown.footer}
          </footer>
        )}
      </article>
    </section>,
    document.body,
  );
}
