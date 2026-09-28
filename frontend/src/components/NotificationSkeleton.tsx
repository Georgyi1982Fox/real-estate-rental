/** Скелетон карточки уведомления */
export default function NotificationSkeleton() {
  return (
    <article
      className="notification-skeleton flex animate-pulse items-start gap-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4"
      aria-hidden="true"
    >
      <div className="size-10 shrink-0 rounded-full bg-[var(--surface-hover)]" />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <div className="h-4 w-5/6 rounded bg-[var(--surface-hover)]" />
        <div className="h-3 w-1/2 rounded bg-[var(--surface-hover)]" />
        <div className="h-3 w-1/4 rounded bg-[var(--surface-hover)]" />
      </div>
      <div className="size-16 shrink-0 rounded-[var(--radius-sm)] bg-[var(--surface-hover)]" />
    </article>
  );
}
