const BLOCK = 'rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)]';

interface ProfileSkeletonProps {
  /** Аватар и имя тоже грузятся (браузер ждёт /api/auth/me) */
  withHeader?: boolean;
}

/** Скелетон профиля: плитки статистики и карточка подписки */
export default function ProfileSkeleton({ withHeader = false }: ProfileSkeletonProps) {
  return (
    <div className="profile-skeleton flex animate-pulse flex-col gap-6" aria-hidden="true">
      {withHeader && (
        <div className="flex flex-col items-center gap-3 pt-2">
          <div className="size-24 rounded-full bg-[var(--surface-hover)]" />
          <div className="h-7 w-1/2 max-w-48 rounded bg-[var(--surface-hover)]" />
          <div className="h-4 w-1/3 max-w-32 rounded bg-[var(--surface-hover)]" />
        </div>
      )}
      <div className="grid grid-cols-2 gap-3">
        {[0, 1].map((index) => (
          <div key={index} className={`${BLOCK} flex flex-col gap-2 p-4`}>
            <div className="size-9 rounded-full bg-[var(--surface-hover)]" />
            <div className="h-7 w-10 rounded bg-[var(--surface-hover)]" />
            <div className="h-4 w-3/4 rounded bg-[var(--surface-hover)]" />
          </div>
        ))}
      </div>
      <div className={`${BLOCK} flex flex-col gap-4 p-5`}>
        <div className="flex items-center gap-3">
          <div className="size-11 rounded-full bg-[var(--surface-hover)]" />
          <div className="h-6 w-1/3 rounded bg-[var(--surface-hover)]" />
        </div>
        <div className="h-5 w-full rounded bg-[var(--surface-hover)]" />
        <div className="h-11 w-full rounded-[var(--radius-md)] bg-[var(--surface-hover)]" />
      </div>
    </div>
  );
}
