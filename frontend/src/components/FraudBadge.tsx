import { useEffect, useId, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { Link } from 'react-router-dom';
import type { FraudLevel, ListingId } from '../api/types';
import { fraudReasonTexts } from '../lib/fraud';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

/** Якорь блока предупреждения на странице объявления: «Подробнее» ведёт к нему */
export const FRAUD_WARNING_HASH = '#fraud-warning';

interface FraudBadgeProps {
  listingId: ListingId;
  level: Exclude<FraudLevel, 'none'>;
  /** Коды причин из объявления (fraud_reasons) */
  reasons: string[];
}

/**
 * Жёлтый кружок ⚠️ в углу карточки: у объявления есть признаки мошенничества.
 * Нажатие не открывает квартиру, а показывает подсказку с причинами и ссылкой «Подробнее»;
 * на компьютере она появляется и по наведению мыши. Закрывается нажатием вне её,
 * повторным нажатием на кружок или Esc.
 */
export default function FraudBadge({ listingId, level, reasons }: FraudBadgeProps) {
  const { t } = useI18n();
  const ft = t.listing.fraud;
  const tipId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  // hover — открыта наведением мыши и закроется, когда мышь уйдёт; pinned — открыта нажатием.
  // Щелчок по наведённой подсказке закрепляет её, а не закрывает
  const [mode, setMode] = useState<'closed' | 'hover' | 'pinned'>('closed');
  const open = mode !== 'closed';
  const texts = fraudReasonTexts(reasons, ft.reasons);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (event.target instanceof Node && !rootRef.current?.contains(event.target)) {
        setMode('closed');
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMode('closed');
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  // Касание тоже присылает pointerenter — наведением считаем только мышь
  const onHover = (inside: boolean) => (event: ReactPointerEvent) => {
    if (event.pointerType !== 'mouse') return;
    setMode((value) => {
      if (inside) return value === 'closed' ? 'hover' : value;
      return value === 'hover' ? 'closed' : value;
    });
  };

  return (
    // Лежит поверх «растянутой» ссылки карточки; сам контейнер нажатия пропускает
    <div
      ref={rootRef}
      className="fraud-badge pointer-events-none absolute inset-x-3 top-4 z-20 flex flex-col items-start"
      onPointerEnter={onHover(true)}
      onPointerLeave={onHover(false)}
    >
      <button
        type="button"
        className="fraud-badge__button pointer-events-auto relative inline-flex size-9 items-center justify-center rounded-full border border-white/60 bg-[var(--accent)] text-[var(--warning-ink)] shadow-[var(--shadow-md)] transition-transform duration-200 after:absolute after:-inset-1 after:content-[''] active:scale-[.95]"
        aria-label={t.card.fraud}
        aria-expanded={open}
        aria-controls={tipId}
        onClick={() => {
          haptic('light');
          setMode((value) => (value === 'pinned' ? 'closed' : 'pinned'));
        }}
      >
        <Icon name="alert" className="size-5" />
      </button>

      {open && (
        // pt вместо отступа: между кружком и подсказкой нет щели, где наведение бы пропало
        <section
          id={tipId}
          className="fraud-badge__tip pointer-events-auto w-full max-w-xs pt-1.5"
          aria-label={t.card.fraud}
        >
          <div className="fraud-badge__body space-y-2 rounded-[var(--radius-md)] border border-[var(--warning-border)] bg-[var(--surface)] p-3 text-sm leading-5 text-[var(--text-primary)] shadow-[var(--shadow-lg)]">
            <p className="fraud-badge__title m-0 font-semibold">
              {level === 'high' ? ft.high : t.card.fraud_title}
            </p>
            {texts.length > 0 && (
              <ul
                className="fraud-badge__reasons list-disc space-y-1 pl-5 text-[var(--text-secondary)]"
                aria-label={ft.reasons_label}
              >
                {texts.map((text) => (
                  <li key={text}>{text}</li>
                ))}
              </ul>
            )}
            <Link
              to={`/listing/${encodeURIComponent(listingId)}${FRAUD_WARNING_HASH}`}
              className="fraud-badge__more inline-flex min-h-9 items-center gap-1 rounded-[var(--radius-sm)] font-semibold underline underline-offset-2"
              onClick={() => haptic('light')}
            >
              {t.card.fraud_more}
              <Icon name="chevron" className="size-4" />
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
