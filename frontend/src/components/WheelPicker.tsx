import type { KeyboardEvent } from 'react';
import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import { haptic } from '../lib/telegram';

interface WheelPickerOption<T extends string> {
  value: T;
  label: string;
}

interface WheelPickerProps<T extends string> {
  options: WheelPickerOption<T>[];
  value: T;
  onChange: (next: T) => void;
  'aria-labelledby': string;
  className?: string;
}

/** Сколько ждать после последнего scroll-события, чтобы считать барабан остановившимся */
const SETTLE_MS = 130;
/** Запасная высота строки (px), пока рефы ещё не отрисованы */
const FALLBACK_ROW_PX = 36;

/**
 * Барабан-пикер: вертикальная колонка значений на общем фоне вместо выпадающего списка.
 * Переключение — свайпом/колесом мыши/стрелками, соседние значения видны частично.
 */
export default function WheelPicker<T extends string>({
  options,
  value,
  onChange,
  'aria-labelledby': labelledBy,
  className = '',
}: WheelPickerProps<T>) {
  const listRef = useRef<HTMLDivElement>(null);
  const rowRef = useRef<HTMLDivElement>(null);
  const settleTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const baseId = useId();

  const committedIndex = useMemo(() => {
    const index = options.findIndex((option) => option.value === value);
    return index < 0 ? 0 : index;
  }, [options, value]);
  const [visualIndex, setVisualIndex] = useState(committedIndex);

  const rowHeight = () => rowRef.current?.offsetHeight || FALLBACK_ROW_PX;

  const scrollToIndex = useCallback((index: number, behavior: ScrollBehavior) => {
    listRef.current?.scrollTo({ top: index * rowHeight(), behavior });
  }, []);

  // Значение сменилось не из-за скролла (например, сброс фильтров снаружи) — довести барабан без анимации
  useEffect(() => {
    setVisualIndex(committedIndex);
    scrollToIndex(committedIndex, 'auto');
  }, [committedIndex, scrollToIndex]);

  const commit = useCallback(
    (index: number) => {
      const clamped = Math.min(Math.max(index, 0), options.length - 1);
      setVisualIndex(clamped);
      if (clamped === committedIndex) return;
      const option = options[clamped];
      if (!option) return;
      haptic('selection');
      onChange(option.value);
    },
    [committedIndex, onChange, options],
  );

  const handleScroll = () => {
    const nearest = Math.round((listRef.current?.scrollTop ?? 0) / rowHeight());
    const clamped = Math.min(Math.max(nearest, 0), options.length - 1);
    setVisualIndex(clamped);
    if (settleTimer.current) clearTimeout(settleTimer.current);
    settleTimer.current = setTimeout(() => commit(clamped), SETTLE_MS);
  };

  const goTo = (index: number) => {
    if (settleTimer.current) clearTimeout(settleTimer.current);
    const clamped = Math.min(Math.max(index, 0), options.length - 1);
    scrollToIndex(clamped, 'smooth');
    commit(clamped);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      goTo(visualIndex + 1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      goTo(visualIndex - 1);
    } else if (event.key === 'Home') {
      event.preventDefault();
      goTo(0);
    } else if (event.key === 'End') {
      event.preventDefault();
      goTo(options.length - 1);
    }
  };

  return (
    <div
      ref={listRef}
      role="listbox"
      tabIndex={0}
      aria-labelledby={labelledBy}
      aria-activedescendant={`${baseId}-${visualIndex}`}
      className={`wheel-picker no-scrollbar h-[6.75rem] touch-pan-y select-none snap-y snap-mandatory overflow-y-auto overscroll-contain rounded-[var(--radius-md)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] focus-visible:ring-offset-2 ${className}`}
      onScroll={handleScroll}
      onKeyDown={handleKeyDown}
    >
      <div aria-hidden="true" className="h-9" />
      {options.map((option, index) => (
        <div
          key={option.value}
          ref={index === 0 ? rowRef : undefined}
          id={`${baseId}-${index}`}
          role="option"
          aria-selected={index === committedIndex}
          className={`wheel-picker__option flex h-9 cursor-pointer snap-center items-center justify-center text-center text-sm ${
            index === visualIndex
              ? 'wheel-picker__option--active font-semibold text-[var(--text-primary)]'
              : 'wheel-picker__option--peek text-[var(--text-secondary)]'
          }`}
          onClick={() => goTo(index)}
        >
          <span className="truncate">{option.label}</span>
        </div>
      ))}
      <div aria-hidden="true" className="h-9" />
    </div>
  );
}
