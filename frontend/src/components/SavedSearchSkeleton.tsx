/** Скелетон карточки сохранённого поиска */
export default function SavedSearchSkeleton() {
  return (
    <article
      className="saved-search-skeleton animate-pulse rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4"
      aria-hidden="true"
    >
      <div className="h-5 w-2/3 rounded bg-[var(--surface-hover)]" />
      <div className="mt-2 h-4 w-1/2 rounded bg-[var(--surface-hover)]" />
      <div className="mt-5 h-7 w-full rounded bg-[var(--surface-hover)]" />
      <div className="mt-4 h-9 w-full rounded bg-[var(--surface-hover)]" />
    </article>
  );
}
