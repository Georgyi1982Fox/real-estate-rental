import { useCallback, useEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { fill } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';

interface GalleryProps {
  images: string[];
  /** Базовый alt, к нему добавляется номер фото */
  alt: string;
}

const SCROLL_DEBOUNCE_MS = 60;

const ARROW_CLASS =
  'gallery__arrow absolute top-1/2 hidden size-10 -translate-y-1/2 place-items-center rounded-full bg-[var(--surface)]/90 text-lg text-[var(--text-primary)] shadow-[var(--shadow-md)] backdrop-blur-sm transition-opacity duration-200 hover:bg-[var(--surface)] disabled:opacity-0 md:grid';

/** Галерея фото: нативный свайп (CSS scroll-snap), стрелки на десктопе, точки-навигация */
export default function Gallery({ images, alt }: GalleryProps) {
  const { t } = useI18n();
  const trackRef = useRef<HTMLUListElement>(null);
  const debounceRef = useRef<number | undefined>(undefined);
  const [current, setCurrent] = useState(0);
  const [failed, setFailed] = useState<ReadonlySet<number>>(new Set());
  const total = images.length;

  useEffect(() => () => window.clearTimeout(debounceRef.current), []);

  // Индекс текущего фото считаем из позиции прокрутки (свайп пальцем)
  const handleScroll = () => {
    window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      const track = trackRef.current;
      if (!track?.clientWidth) return;
      setCurrent(Math.round(track.scrollLeft / track.clientWidth));
    }, SCROLL_DEBOUNCE_MS);
  };

  const goTo = useCallback(
    (index: number) => {
      const track = trackRef.current;
      if (!track) return;
      const target = Math.max(0, Math.min(total - 1, index));
      track.scrollTo({ left: target * track.clientWidth, behavior: 'smooth' });
      setCurrent(target);
    },
    [total],
  );

  const handleKeyDown = (event: KeyboardEvent<HTMLUListElement>) => {
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      goTo(current + 1);
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      goTo(current - 1);
    }
  };

  if (total === 0) {
    return (
      <figure className="gallery gallery--empty grid aspect-[4/3] w-full place-items-center rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] bg-[var(--surface-hover)] sm:aspect-[16/10]">
        <figcaption className="flex flex-col items-center gap-2 text-sm text-[var(--text-secondary)]">
          <span className="text-3xl" aria-hidden="true">
            🏠
          </span>
          {t.card.no_photo}
        </figcaption>
      </figure>
    );
  }

  return (
    <section className="gallery relative" aria-roledescription="carousel" aria-label={t.gallery.label}>
      <ul
        ref={trackRef}
        className="gallery__track no-scrollbar flex aspect-[4/3] w-full list-none snap-x snap-mandatory overflow-x-auto overscroll-x-contain rounded-[var(--radius-lg)] bg-[var(--surface-hover)] p-0 sm:aspect-[16/10]"
        tabIndex={0}
        aria-label={t.gallery.label}
        onScroll={handleScroll}
        onKeyDown={handleKeyDown}
      >
        {images.map((src, index) => (
          <li
            key={src + index}
            className="gallery__slide relative h-full w-full shrink-0 snap-center"
            aria-roledescription="slide"
            aria-label={`${index + 1} / ${total}`}
          >
            {/* Фолбэк под картинкой: виден, если фото не загрузилось */}
            <span className="gallery__fallback absolute inset-0 grid place-items-center text-sm text-[var(--text-secondary)]">
              {t.card.no_photo}
            </span>
            {!failed.has(index) && (
              <img
                className="gallery__image relative h-full w-full select-none object-cover"
                src={src}
                alt={`${alt} — ${index + 1}`}
                width={800}
                height={600}
                loading={index === 0 ? 'eager' : 'lazy'}
                fetchPriority={index === 0 ? 'high' : undefined}
                draggable={false}
                onError={() => setFailed((set) => new Set(set).add(index))}
              />
            )}
          </li>
        ))}
      </ul>

      <p
        className="gallery__counter pointer-events-none absolute right-3 top-3 rounded-full bg-black/55 px-2.5 py-1 text-xs font-medium text-white backdrop-blur-sm"
        aria-live="polite"
      >
        {current + 1} / {total}
      </p>

      {total > 1 && (
        <>
          <button
            type="button"
            className={`${ARROW_CLASS} gallery__arrow--prev left-3`}
            aria-label={t.gallery.prev}
            disabled={current === 0}
            onClick={() => goTo(current - 1)}
          >
            <span aria-hidden="true">‹</span>
          </button>
          <button
            type="button"
            className={`${ARROW_CLASS} gallery__arrow--next right-3`}
            aria-label={t.gallery.next}
            disabled={current === total - 1}
            onClick={() => goTo(current + 1)}
          >
            <span aria-hidden="true">›</span>
          </button>

          <nav className="gallery__dots absolute inset-x-0 bottom-2 flex justify-center gap-0.5" aria-label={t.gallery.label}>
            {images.map((src, index) => (
              <button
                key={src + index}
                type="button"
                className="gallery__dot grid size-6 place-items-center"
                aria-label={fill(t.gallery.go_to, index + 1)}
                aria-current={current === index ? 'true' : 'false'}
                onClick={() => goTo(index)}
              >
                <span
                  className={`block h-1.5 rounded-full bg-white shadow-[var(--shadow-sm)] transition-all duration-200 ${current === index ? 'w-4 opacity-100' : 'w-1.5 opacity-60'}`}
                  aria-hidden="true"
                />
              </button>
            ))}
          </nav>
        </>
      )}
    </section>
  );
}
