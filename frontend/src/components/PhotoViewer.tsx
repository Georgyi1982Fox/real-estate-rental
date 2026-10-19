import { useCallback, useEffect, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { createPortal } from 'react-dom';
import { useTelegramBack } from '../hooks/useTelegramBackButton';
import { fill } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

interface PhotoViewerProps {
  images: string[];
  /** Какое фото открыть; null — просмотр закрыт */
  start: number | null;
  alt: string;
  /** Закрыли; index — фото, на котором остановились (галерея на странице переходит к нему) */
  onClose: (index: number) => void;
}

const MAX_SCALE = 4;
const DOUBLE_TAP_SCALE = 2.5;
const DOUBLE_TAP_MS = 300;
/** Палец сдвинулся меньше — это нажатие, а не свайп */
const TAP_SLOP_PX = 10;

interface Point {
  x: number;
  y: number;
}

interface Zoom {
  scale: number;
  x: number;
  y: number;
}

const NO_ZOOM: Zoom = { scale: 1, x: 0, y: 0 };

const distance = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.y - b.y);

interface ZoomableProps {
  src: string;
  alt: string;
  /** Это фото сейчас на экране: только его можно увеличить, ушло с экрана — масштаб сброшен */
  active: boolean;
  /** Грузить сразу (текущее и соседние), остальные — когда до них долистают */
  eager: boolean;
  /** Фото увеличено: лента не листается, палец двигает фото */
  onZoomChange: (zoomed: boolean) => void;
}

/** Фото на весь экран: двойное нажатие — увеличить/вернуть, двумя пальцами — масштаб, одним — сдвиг */
function Zoomable({ src, alt, active, eager, onZoomChange }: ZoomableProps) {
  const [zoom, setZoom] = useState<Zoom>(NO_ZOOM);
  const pointers = useRef(new Map<number, Point>());
  // Начало жеста: масштаб, сдвиг и расстояние между пальцами
  const gesture = useRef<{ zoom: Zoom; spread: number; origin: Point } | null>(null);
  const lastTap = useRef(0);
  const downAt = useRef<Point | null>(null);
  const zoomed = zoom.scale > 1;

  // Долистали до другого фото — это возвращается к обычному размеру
  useEffect(() => {
    if (!active) setZoom(NO_ZOOM);
  }, [active]);

  useEffect(() => {
    if (active) onZoomChange(zoomed);
  }, [active, zoomed, onZoomChange]);

  const apply = (next: Zoom) => setZoom(next.scale <= 1.01 ? NO_ZOOM : next);

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    downAt.current = pointers.current.size === 1 ? { x: event.clientX, y: event.clientY } : null;
    const points = [...pointers.current.values()];
    const [first, second] = points;
    if (first && second) {
      gesture.current = { zoom, spread: distance(first, second), origin: first };
    } else if (first) {
      gesture.current = { zoom, spread: 0, origin: first };
    }
    // Палец двигает увеличенное фото, а не ленту
    if (zoomed || points.length > 1) event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!pointers.current.has(event.pointerId) || !gesture.current) return;
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const [first, second] = [...pointers.current.values()];
    const start = gesture.current;
    if (first && second && start.spread > 0) {
      const scale = Math.min(MAX_SCALE, Math.max(1, (start.zoom.scale * distance(first, second)) / start.spread));
      apply({ ...start.zoom, scale });
    } else if (first && zoomed) {
      apply({
        scale: start.zoom.scale,
        x: start.zoom.x + (first.x - start.origin.x),
        y: start.zoom.y + (first.y - start.origin.y),
      });
    }
  };

  const release = (pointerId: number) => {
    pointers.current.delete(pointerId);
    const rest = [...pointers.current.values()][0];
    // Отпустили один палец из двух — дальше двигаем оставшимся
    gesture.current = rest ? { zoom, spread: 0, origin: rest } : null;
  };

  // Браузер забрал жест себе (свайп ленты) — это не нажатие
  const onPointerCancel = (event: ReactPointerEvent<HTMLDivElement>) => {
    release(event.pointerId);
    downAt.current = null;
    lastTap.current = 0;
  };

  const onPointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    const wasPinch = pointers.current.size > 1;
    release(event.pointerId);
    const down = downAt.current;
    const tap =
      !wasPinch &&
      pointers.current.size === 0 &&
      down !== null &&
      distance(down, { x: event.clientX, y: event.clientY }) < TAP_SLOP_PX;
    if (!tap) {
      lastTap.current = 0;
      return;
    }
    const now = Date.now();
    if (now - lastTap.current < DOUBLE_TAP_MS) {
      lastTap.current = 0;
      haptic('light');
      if (zoomed) {
        setZoom(NO_ZOOM);
      } else {
        // Увеличиваем то место, куда нажали
        const box = event.currentTarget.getBoundingClientRect();
        const dx = event.clientX - (box.left + box.width / 2);
        const dy = event.clientY - (box.top + box.height / 2);
        setZoom({ scale: DOUBLE_TAP_SCALE, x: -dx * (DOUBLE_TAP_SCALE - 1), y: -dy * (DOUBLE_TAP_SCALE - 1) });
      }
    } else {
      lastTap.current = now;
    }
  };

  return (
    <div
      className="photo-viewer__zoom grid h-full w-full place-items-center overflow-hidden"
      style={{ touchAction: zoomed ? 'none' : 'pan-x' }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerCancel}
    >
      <img
        className="photo-viewer__image max-h-full max-w-full select-none object-contain"
        style={{
          transform: `translate(${zoom.x}px, ${zoom.y}px) scale(${zoom.scale})`,
          transition: pointers.current.size > 0 ? 'none' : 'transform 200ms ease',
          cursor: zoomed ? 'grab' : 'zoom-in',
        }}
        src={src}
        alt={alt}
        loading={eager ? 'eager' : 'lazy'}
        draggable={false}
      />
    </div>
  );
}

/**
 * Фото на весь экран поверх страницы: листать свайпом, стрелками по бокам или миниатюрами
 * внизу, увеличивать (двойное нажатие или двумя пальцами), закрыть крестиком, Esc или «Назад»
 */
export default function PhotoViewer({ images, start, alt, onClose }: PhotoViewerProps) {
  const { t } = useI18n();
  const trackRef = useRef<HTMLUListElement>(null);
  const thumbsRef = useRef<HTMLUListElement>(null);
  const [current, setCurrent] = useState(start ?? 0);
  const [zoomed, setZoomed] = useState(false);
  const total = images.length;
  const open = start !== null;
  const close = useCallback(() => onClose(current), [onClose, current]);
  // «Назад» Telegram закрывает фото, а не страницу (приоритет — как у модалки)
  useTelegramBack(close, open, 1);

  // Миниатюра текущего фото всегда видна в полоске
  useEffect(() => {
    if (!open) return;
    const thumb = thumbsRef.current?.children[current];
    if (thumb instanceof HTMLElement) {
      thumb.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    }
  }, [open, current]);

  const goTo = useCallback(
    (index: number) => {
      const track = trackRef.current;
      if (!track || total === 0) return;
      const next = (index + total) % total;
      track.scrollTo({ left: next * track.clientWidth, behavior: 'smooth' });
    },
    [total],
  );

  // Открыли — сразу на нужном фото, страница под окном не прокручивается
  useEffect(() => {
    if (!open) return;
    setCurrent(start);
    const track = trackRef.current;
    if (track) track.scrollLeft = start * track.clientWidth;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = overflow;
    };
  }, [open, start]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close();
      else if (event.key === 'ArrowRight') goTo(current + 1);
      else if (event.key === 'ArrowLeft') goTo(current - 1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, current, goTo, close]);

  if (!open) return null;

  // Стрелки видны и на телефоне: не все догадываются листать свайпом
  const arrow = (direction: -1 | 1) => (
    <button
      type="button"
      className={`photo-viewer__arrow absolute top-1/2 grid size-10 -translate-y-1/2 place-items-center rounded-full bg-black/45 text-white backdrop-blur-sm hover:bg-black/65 active:scale-95 md:size-12 ${
        direction < 0 ? 'left-2 md:left-4' : 'right-2 md:right-4'
      }`}
      aria-label={direction < 0 ? t.gallery.prev : t.gallery.next}
      onClick={() => {
        haptic('selection');
        goTo(current + direction);
      }}
    >
      <Icon name="chevron" className={`size-6 ${direction < 0 ? 'rotate-180' : ''}`} />
    </button>
  );

  return createPortal(
    <div
      className="photo-viewer fixed inset-0 z-50 flex flex-col bg-black pt-[var(--safe-top)] pb-[var(--safe-bottom)]"
      role="dialog"
      aria-modal="true"
      aria-label={t.gallery.label}
    >
      <header className="photo-viewer__bar flex items-center justify-between gap-3 px-4 py-3 text-white">
        <p className="m-0 text-sm font-medium tabular-nums" aria-live="polite">
          {current + 1} / {total}
        </p>
        <button
          type="button"
          className="photo-viewer__close inline-grid size-10 place-items-center rounded-full bg-white/15 hover:bg-white/25"
          aria-label={t.common.close}
          onClick={close}
        >
          <Icon name="close" className="size-5" />
        </button>
      </header>

      <div className="relative min-h-0 flex-1">
        <ul
          ref={trackRef}
          className={`photo-viewer__track no-scrollbar flex h-full w-full list-none snap-x snap-mandatory p-0 ${
            zoomed ? 'overflow-hidden' : 'overflow-x-auto overscroll-x-contain'
          }`}
          onScroll={(event) => {
            const track = event.currentTarget;
            const index = Math.round(track.scrollLeft / Math.max(1, track.clientWidth));
            if (index !== current && index >= 0 && index < total) setCurrent(index);
          }}
        >
          {/* Ключи постоянные: фото под пальцем не перерисовывается посреди свайпа
              (иначе телефон обрывает свайп и лента возвращается назад) */}
          {images.map((src, index) => (
            <li key={src + index} className="h-full w-full shrink-0 snap-center">
              <Zoomable
                src={src}
                alt={`${alt} — ${index + 1}`}
                active={index === current}
                eager={Math.abs(index - current) <= 1}
                onZoomChange={setZoomed}
              />
            </li>
          ))}
        </ul>
        {total > 1 && !zoomed && (
          <>
            {arrow(-1)}
            {arrow(1)}
          </>
        )}
      </div>

      {/* Миниатюры: нажали — сразу к этому фото */}
      {total > 1 && (
        <ul
          ref={thumbsRef}
          className="photo-viewer__thumbs no-scrollbar m-0 flex shrink-0 list-none gap-2 overflow-x-auto px-4 py-3"
          aria-label={t.gallery.label}
        >
          {images.map((src, index) => (
            <li key={src + index} className="shrink-0">
              <button
                type="button"
                className={`photo-viewer__thumb block size-14 overflow-hidden rounded-lg transition-opacity duration-200 ${
                  index === current
                    ? 'opacity-100 ring-2 ring-white'
                    : 'opacity-50 hover:opacity-80'
                }`}
                aria-label={fill(t.gallery.go_to, index + 1)}
                aria-current={index === current ? 'true' : undefined}
                onClick={() => {
                  haptic('selection');
                  goTo(index);
                }}
              >
                <img
                  className="h-full w-full object-cover"
                  src={src}
                  alt=""
                  loading="lazy"
                  draggable={false}
                />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>,
    document.body,
  );
}
