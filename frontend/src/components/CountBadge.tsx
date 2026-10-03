interface CountBadgeProps {
  count: number;
  /** Больше max показываем как «max+» */
  max: number;
}

/**
 * Счётчик в углу иконки; число озвучивает aria-label ссылки.
 * Обводка цвета фона отделяет его от иконки и цветного кружка под ней.
 */
export default function CountBadge({ count, max }: CountBadgeProps) {
  if (count <= 0) return null;
  return (
    <span
      className="count-badge absolute -right-0.5 -top-0.5 inline-flex min-h-5 min-w-5 items-center justify-center rounded-full bg-[var(--badge)] px-1 text-[11px] font-bold leading-none text-[var(--badge-text)] ring-2 ring-[var(--background)]"
      aria-hidden="true"
    >
      {count > max ? `${max}+` : count}
    </span>
  );
}
