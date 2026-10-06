import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCarousel } from '../hooks/useCarousel';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

interface CardGalleryProps {
  images: string[];
  /** Базовый alt, к нему добавляется номер фото */
  alt: string;
  /** Страница объявления: нажатие на фото открывает её, как и вся карточка */
  to: string;
}

const ARROW_CLASS =
  'card-gallery__arrow absolute top-1/2 z-10 hidden size-8 -translate-y-1/2 place-items-center rounded-full bg-white/90 text-base leading-none text-[var(--text-primary)] opacity-0 shadow-[var(--shadow-sm)] backdrop-blur-sm transition-opacity duration-200 hover:bg-white group-hover:opacity-100 md:grid';

/**
 * Фото в карточке объявления: листаются свайпом по кругу, на десктопе — стрелки при наведении.
 * Лента лежит поверх «растянутой» ссылки карточки (иначе свайп до неё не доходит),
 * поэтому каждое фото — своя ссылка на объявление; для клавиатуры и скринридера
 * остаётся одна ссылка — заголовок карточки.
 */
export default function CardGallery({ images, alt, to }: CardGalleryProps) {
  const { t } = useI18n();
  const [failed, setFailed] = useState<ReadonlySet<number>>(new Set());
  const total = images.length;
  const { trackRef, slides, current, onScroll, goTo } = useCarousel(total);

  return (
    <>
      <ul
        ref={trackRef}
        className="card-gallery no-scrollbar relative z-10 m-0 flex h-full w-full list-none snap-x snap-mandatory overflow-x-auto overscroll-x-contain p-0"
        onScroll={onScroll}
      >
        {slides.map(({ index, clone }, position) => (
          <li
            key={position}
            className="card-gallery__slide relative h-full w-full shrink-0 snap-center snap-always overflow-hidden"
            aria-hidden={clone || undefined}
          >
            {/* Фолбэк под картинкой: виден, если фото не загрузилось */}
            <span className="card-gallery__fallback absolute inset-0 grid place-items-center text-sm text-[var(--text-secondary)]">
              {t.card.no_photo}
            </span>
            <Link
              to={to}
              className="card-gallery__link relative block h-full w-full"
              tabIndex={-1}
              aria-hidden="true"
              draggable={false}
              onClick={() => haptic('light')}
            >
              {!failed.has(index) && (
                <img
                  className="card-gallery__image h-full w-full select-none object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                  src={images[index]}
                  alt={index === 0 && !clone ? alt : `${alt} — ${index + 1}`}
                  loading="lazy"
                  width={400}
                  height={300}
                  draggable={false}
                  onError={() => setFailed((set) => new Set(set).add(index))}
                />
              )}
            </Link>
          </li>
        ))}
      </ul>

      {/* Стрелки — только для мыши: с клавиатуры все фото доступны на странице объявления */}
      <button
        type="button"
        className={`${ARROW_CLASS} card-gallery__arrow--prev left-2`}
        aria-label={t.gallery.prev}
        tabIndex={-1}
        onClick={() => goTo(current - 1)}
      >
        <span aria-hidden="true">‹</span>
      </button>
      <button
        type="button"
        className={`${ARROW_CLASS} card-gallery__arrow--next right-2`}
        aria-label={t.gallery.next}
        tabIndex={-1}
        onClick={() => goTo(current + 1)}
      >
        <span aria-hidden="true">›</span>
      </button>

      <p className="card-gallery__counter pointer-events-none absolute bottom-2 right-2 z-10 m-0 rounded-full bg-black/55 px-2 py-0.5 text-xs font-medium leading-5 text-white backdrop-blur-sm">
        <span className="sr-only">{t.gallery.label}: </span>
        {current + 1} / {total}
      </p>
    </>
  );
}
