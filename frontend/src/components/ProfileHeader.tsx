import type { AuthUser } from '../api/types';
import Avatar from './Avatar';

interface ProfileHeaderProps {
  user: AuthUser;
}

/** Шапка профиля: аватар, имя и @username — из Telegram (бэкенд имя не хранит) */
export default function ProfileHeader({ user }: ProfileHeaderProps) {
  const name = [user.first_name, user.last_name].filter(Boolean).join(' ').trim();
  // В браузере username нет — показываем email, если вход был через Google/email
  const subtitle = user.username ? `@${user.username}` : user.email;

  return (
    <header className="profile-header flex flex-col items-center gap-3 pt-2 text-center">
      <Avatar
        user={user}
        className="profile-header__avatar size-24 text-4xl shadow-[var(--shadow-md)] ring-4 ring-[var(--surface)]"
      />
      <hgroup className="profile-header__names min-w-0 max-w-full">
        <h1 className="text-2xl font-bold tracking-tight">{name || subtitle}</h1>
        {name && subtitle && (
          <p className="mt-1 text-sm text-[var(--text-secondary)]">{subtitle}</p>
        )}
      </hgroup>
    </header>
  );
}
