/**
 * Заглушка блока страницы квартиры, пока скачивается его часть сайта (FRONTEND-054).
 * Та же рамка и примерно та же высота, что у блока, — страница не прыгает
 */
export default function ListingBlockSkeleton({ height }: { height: string }) {
  return (
    <div
      className={`listing-block-skeleton animate-pulse space-y-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 ${height}`}
      aria-busy="true"
      aria-hidden="true"
    >
      <div className="h-6 w-1/2 rounded bg-[var(--surface-hover)]" />
      <div className="h-4 w-3/4 rounded bg-[var(--surface-hover)]" />
    </div>
  );
}
