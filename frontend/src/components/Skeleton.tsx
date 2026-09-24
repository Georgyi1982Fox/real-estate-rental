/** Скелетон карточки объявления на время загрузки */
export default function Skeleton() {
  return (
    <article
      className="skeleton animate-pulse rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4"
      aria-hidden="true"
    >
      <div className="aspect-[4/3] rounded-[var(--radius-md)] bg-[var(--surface-hover)]" />
      <div className="mt-4 h-5 w-2/3 rounded bg-[var(--surface-hover)]" />
      <div className="mt-2 h-4 w-1/2 rounded bg-[var(--surface-hover)]" />
    </article>
  );
}
