interface CountBadgeProps {
  count: number;
  /** Больше max показываем как «max+» */
  max: number;
}

/** Красный счётчик в углу иконки шапки; число озвучивает aria-label ссылки */
export default function CountBadge({ count, max }: CountBadgeProps) {
  if (count <= 0) return null;
  return (
    <span
      className="count-badge absolute -right-0.5 -top-0.5 inline-flex min-h-5 min-w-5 items-center justify-center rounded-full bg-[var(--danger)] px-1 text-[11px] font-bold leading-none text-white"
      aria-hidden="true"
    >
      {count > max ? `${max}+` : count}
    </span>
  );
}
