import { useId } from 'react';
import type { ReactNode } from 'react';

interface ProfileSectionProps {
  title: string;
  /** nav — для блока-меню со ссылками */
  as?: 'section' | 'nav';
  /** Строки списка: элементы <li> */
  children: ReactNode;
}

/** Группа строк профиля в стиле настроек Telegram: заголовок и карточка-список */
export default function ProfileSection({
  title,
  as: Tag = 'section',
  children,
}: ProfileSectionProps) {
  const titleId = useId();

  return (
    <Tag className="profile-section flex flex-col gap-2" aria-labelledby={titleId}>
      <h2 id={titleId} className="px-1 text-sm font-semibold text-[var(--text-secondary)]">
        {title}
      </h2>
      <ul className="profile-section__list divide-y divide-[var(--border)] overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)]">
        {children}
      </ul>
    </Tag>
  );
}
