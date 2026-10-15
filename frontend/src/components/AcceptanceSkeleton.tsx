const ROWS = [0, 1, 2];

/** Скелетон чек-листа приёмки на время загрузки */
export default function AcceptanceSkeleton() {
  return (
    <ul className="acceptance-skeleton m-0 flex list-none flex-col gap-4 p-0" aria-hidden="true">
      {ROWS.map((row) => (
        <li
          key={row}
          className="animate-pulse rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4"
        >
          <span className="block h-5 w-1/3 rounded bg-[var(--surface-hover)]" />
          <span className="mt-4 block h-4 w-2/3 rounded bg-[var(--surface-hover)]" />
          <span className="mt-2 block h-11 rounded-[var(--radius-md)] bg-[var(--surface-hover)]" />
          <span className="mt-4 block h-4 w-1/2 rounded bg-[var(--surface-hover)]" />
          <span className="mt-2 block h-11 rounded-[var(--radius-md)] bg-[var(--surface-hover)]" />
        </li>
      ))}
    </ul>
  );
}
