import { useState } from 'react';
import type { AuthUser } from '../api/types';

interface AvatarProps {
  user: AuthUser;
  /** Tailwind-классы размера, по умолчанию 36px (как иконки в шапке) */
  className?: string;
}

/** Первая буква имени (Array.from — чтобы не разрезать суррогатные пары) */
function initial(user: AuthUser): string {
  const source = user.first_name.trim() || user.username || '?';
  return (Array.from(source)[0] ?? '?').toUpperCase();
}

/** Круглое фото пользователя, а без фото (или если оно не загрузилось) — первая буква имени */
export default function Avatar({ user, className = 'size-9 text-sm' }: AvatarProps) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const photo = user.photo_url && user.photo_url !== failedUrl ? user.photo_url : null;

  return (
    <span
      className={`avatar inline-grid shrink-0 place-items-center overflow-hidden rounded-full bg-[var(--primary)] font-semibold text-white ${className}`}
      aria-hidden="true"
    >
      {photo ? (
        <img
          className="avatar__image size-full object-cover"
          src={photo}
          alt=""
          loading="lazy"
          decoding="async"
          referrerPolicy="no-referrer"
          onError={() => setFailedUrl(photo)}
        />
      ) : (
        <span className="avatar__initial">{initial(user)}</span>
      )}
    </span>
  );
}
