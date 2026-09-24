/** Скелетон страницы квартиры: повторяет раскладку галерея + сводка + детали */
export default function ListingSkeleton() {
  const block = 'rounded-[var(--radius-lg)] bg-[var(--surface-hover)]';

  return (
    <div
      className="listing-skeleton grid animate-pulse grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-8"
      aria-hidden="true"
    >
      <div className={`${block} aspect-[4/3] sm:aspect-[16/10]`} />
      <div className="space-y-4 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 lg:row-span-2">
        <div className="h-7 w-3/4 rounded bg-[var(--surface-hover)]" />
        <div className="h-4 w-1/2 rounded bg-[var(--surface-hover)]" />
        <div className="h-9 w-2/5 rounded bg-[var(--surface-hover)]" />
        <div className="h-12 rounded-[var(--radius-md)] bg-[var(--surface-hover)]" />
        <div className="h-12 rounded-[var(--radius-md)] bg-[var(--surface-hover)]" />
      </div>
      <div className={`${block} h-48`} />
    </div>
  );
}
