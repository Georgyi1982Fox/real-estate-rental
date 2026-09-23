interface EmptyStateProps {
  title: string;
  text?: string;
  icon?: string;
}

export default function EmptyState({ title, text, icon = '🏠' }: EmptyStateProps) {
  return (
    <section className="empty-state flex flex-col items-center gap-2 rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] px-4 py-16 text-center">
      <span className="text-3xl" aria-hidden="true">
        {icon}
      </span>
      <p className="text-sm font-medium text-[var(--text-primary)]">{title}</p>
      {text && <p className="max-w-xs text-sm text-[var(--text-secondary)]">{text}</p>}
    </section>
  );
}
