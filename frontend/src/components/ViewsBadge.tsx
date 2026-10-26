import { useEffect, useId, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import type { ListingId, ListingViews } from '../api/types';
import { useApi } from '../hooks/useApi';
import { fill, plural } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

interface ViewsBadgeProps {
  listingId: ListingId;
  views: number;
  /** Текст значка: «👁 12» на карточке, «👁 12 просмотров» на странице квартиры */
  long?: boolean;
  /**
   * Куда раскрывается подсказка. Она позиционируется по ближайшему родителю с `relative`
   * и тянется на всю его ширину — у карточки это строка цены, подсказка ложится на фото
   */
  placement?: 'above' | 'below';
  className?: string;
}

/**
 * «👁 N» (FRONTEND-046). Нажатие не открывает квартиру, а показывает подсказку: сегодня,
 * за неделю, сколько людей смотрели, у скольких в избранном — только числа, имён нет.
 * На компьютере подсказка появляется и по наведению. Цифры грузятся при первом открытии.
 * Закрывается нажатием вне её, повторным нажатием на значок или Esc.
 */
export default function ViewsBadge({
  listingId,
  views,
  long = false,
  placement = 'above',
  className = '',
}: ViewsBadgeProps) {
  const { lang, t } = useI18n();
  const lt = t.listing;
  const vt = lt.views_tip;
  const tipId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  // Как у FraudBadge: hover — открыта мышью, pinned — нажатием
  const [mode, setMode] = useState<'closed' | 'hover' | 'pinned'>('closed');
  const open = mode !== 'closed';
  // Запрос — только после первого открытия; потом ответ остаётся до ухода со страницы
  const [requested, setRequested] = useState(false);
  const stats = useApi<ListingViews>(
    requested ? `/api/listings/${encodeURIComponent(listingId)}/views` : null,
  );

  useEffect(() => {
    if (open) setRequested(true);
  }, [open]);

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

  const onHover = (inside: boolean) => (event: ReactPointerEvent) => {
    if (event.pointerType !== 'mouse') return;
    setMode((value) => {
      if (inside) return value === 'closed' ? 'hover' : value;
      return value === 'hover' ? 'closed' : value;
    });
  };

  const data = stats.data;
  const total = data?.total ?? views;
  const totalText = plural(lt.views, total, lang);
  // Нулевые строки не показываем
  const period = data
    ? [data.today > 0 && fill(vt.today, data.today), data.week > 0 && fill(vt.week, data.week)]
        .filter(Boolean)
        .join(' · ')
    : '';

  return (
    <div
      ref={rootRef}
      className="views-badge inline-flex"
      onPointerEnter={onHover(true)}
      onPointerLeave={onHover(false)}
    >
      <button
        type="button"
        className={`views-badge__button relative z-10 inline-flex items-center gap-1 rounded-full text-xs text-[var(--text-secondary)] underline decoration-dotted underline-offset-2 transition-colors duration-200 hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] ${className}`}
        aria-label={totalText}
        aria-expanded={open}
        aria-controls={tipId}
        onClick={() => {
          haptic('light');
          setMode((value) => (value === 'pinned' ? 'closed' : 'pinned'));
        }}
      >
        <span aria-hidden="true">👁</span>
        <span aria-hidden="true">{long ? plural(lt.views, views, lang) : views}</span>
      </button>

      {open && (
        // Отступ вместо щели: мышь переходит со значка на подсказку, не закрывая её
        <section
          id={tipId}
          className={`views-badge__tip absolute inset-x-0 z-20 ${placement === 'above' ? 'bottom-full pb-1.5' : 'top-full pt-1.5'}`}
          aria-label={vt.label}
          aria-live="polite"
        >
          <div className="views-badge__body max-w-xs space-y-1 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-3 text-sm leading-5 text-[var(--text-primary)] shadow-[var(--shadow-lg)]">
            <p className="views-badge__total m-0 font-semibold">
              <span aria-hidden="true">👁 </span>
              {totalText}
            </p>
            {stats.loading && !data && (
              <span className="views-badge__loading flex min-h-5 items-center text-[var(--text-secondary)]">
                <span className="spinner" aria-hidden="true" />
              </span>
            )}
            {stats.error && !data && (
              <p className="views-badge__error m-0 text-[var(--text-secondary)]">{vt.error}</p>
            )}
            {data && (
              <>
                {period && (
                  <p className="views-badge__period m-0 text-[var(--text-secondary)]">{period}</p>
                )}
                {data.people > 0 && (
                  <p className="views-badge__people m-0 text-[var(--text-secondary)]">
                    {plural(vt.people, data.people, lang)}
                  </p>
                )}
                {data.in_favorites > 0 && (
                  <p className="views-badge__favorites m-0 text-[var(--text-secondary)]">
                    {fill(vt.favorites, data.in_favorites)}
                  </p>
                )}
              </>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
