import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import { haptic } from '../lib/telegram';

const SCROLL_DEBOUNCE_MS = 60;
/** Насколько прокрутка может не дойти до слайда, чтобы считаться остановившейся на нём */
const SNAP_TOLERANCE_PX = 2;

/**
 * Шаг ленты в пикселях. Ширина слайда бывает дробной (карточка в сетке — 343,5px), а
 * clientWidth округлён: на последних слайдах ошибка копилась, и лента не замечала,
 * что стоит на копии. Ширина всей ленты, делённая на число слайдов, даёт точный шаг
 */
function slideStep(track: HTMLUListElement): number {
  return track.childElementCount > 0
    ? track.scrollWidth / track.childElementCount
    : track.clientWidth;
}

export interface CarouselSlide {
  /** Номер фото в исходном списке */
  index: number;
  /** Копия крайнего фото для листания по кругу */
  clone: boolean;
}

export interface Carousel {
  trackRef: RefObject<HTMLUListElement | null>;
  /** Слайды ленты в порядке вёрстки, вместе с копиями по краям */
  slides: CarouselSlide[];
  current: number;
  /** Повесить на onScroll ленты */
  onScroll: () => void;
  /** Плавно перейти к фото; index за краем (−1, total) — переход по кругу */
  goTo: (index: number) => void;
}

/**
 * Лента фото на нативном свайпе (CSS scroll-snap) с листанием по кругу: по краям лежат
 * копии последнего и первого фото. Долистали до копии — незаметно перескакиваем на настоящее.
 */
export function useCarousel(total: number): Carousel {
  const trackRef = useRef<HTMLUListElement>(null);
  const debounceRef = useRef<number | undefined>(undefined);
  const [current, setCurrent] = useState(0);
  const currentRef = useRef(0);
  const loop = total > 1;
  const offset = loop ? 1 : 0;

  const select = useCallback((index: number) => {
    currentRef.current = index;
    setCurrent(index);
  }, []);

  useEffect(() => () => window.clearTimeout(debounceRef.current), []);

  // Лента начинается с копии последнего фото — сразу ставим её на текущее настоящее.
  // То же при смене ширины (поворот экрана, окно): позиция в пикселях иначе съезжает
  useLayoutEffect(() => {
    const track = trackRef.current;
    if (!track) return;
    const align = () =>
      track.scrollTo({
        left: (currentRef.current + offset) * slideStep(track),
        behavior: 'instant',
      });
    align();
    const observer = new ResizeObserver(align);
    observer.observe(track);
    return () => observer.disconnect();
  }, [offset]);

  /** Лента стоит на копии — мгновенно переставляем на настоящее фото; возвращает позицию в ленте */
  const leaveClone = useCallback(
    (track: HTMLUListElement): number => {
      const step = slideStep(track);
      const position = Math.round(track.scrollLeft / step);
      if (!loop) return position;
      // Перескакиваем только когда прокрутка остановилась на слайде, а не на полпути
      if (Math.abs(track.scrollLeft - position * step) > SNAP_TOLERANCE_PX) return position;
      const real = position === 0 ? total : position === total + 1 ? 1 : position;
      if (real !== position) track.scrollTo({ left: real * step, behavior: 'instant' });
      return real;
    },
    [loop, total],
  );

  // Индекс текущего фото считаем из позиции прокрутки (свайп пальцем)
  const onScroll = useCallback(() => {
    window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      const track = trackRef.current;
      if (!track?.clientWidth || total === 0) return;
      const position = leaveClone(track);
      select((((position - offset) % total) + total) % total);
    }, SCROLL_DEBOUNCE_MS);
  }, [leaveClone, offset, select, total]);

  const goTo = useCallback(
    (index: number) => {
      const track = trackRef.current;
      if (!track?.clientWidth || total === 0) return;
      // С последнего фото «вперёд» — на первое, с первого «назад» — на последнее
      const target = ((index % total) + total) % total;
      if (target !== currentRef.current) haptic('selection');
      const from = leaveClone(track);
      // Через край едем на копию (один шаг в ту же сторону), а не назад через всю ленту
      const position = index !== target ? from + Math.sign(index - target) : target + offset;
      track.scrollTo({ left: position * slideStep(track), behavior: 'smooth' });
      select(target);
    },
    [leaveClone, offset, select, total],
  );

  const real = Array.from({ length: total }, (_, index) => ({ index, clone: false }));
  const slides = loop
    ? [{ index: total - 1, clone: true }, ...real, { index: 0, clone: true }]
    : real;

  return { trackRef, slides, current, onScroll, goTo };
}
