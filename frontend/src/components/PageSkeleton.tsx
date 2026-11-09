import Skeleton from './Skeleton';

/** Заглушка, пока догружается часть сайта со страницей (FRONTEND-050) */
export default function PageSkeleton() {
  return (
    <div aria-busy="true">
      <div
        className="skeleton mb-6 h-8 w-1/2 animate-pulse rounded bg-[var(--surface-hover)]"
        aria-hidden="true"
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Skeleton />
        <Skeleton />
      </div>
    </div>
  );
}
