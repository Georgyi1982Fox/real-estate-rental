import { useCallback, useState } from 'react';
import { apiPatch } from '../api/client';
import type { Me, UpdateMeRequest } from '../api/types';
import type { Lang } from '../i18n/strings';
import { useAuth } from '../providers/AuthProvider';
import { useApi } from './useApi';

const ME_PATH = '/api/me';

/** Данные по умолчанию, если /api/me не ответил (сеть, 5xx): профиль остаётся рабочим */
export const FALLBACK_ME: Me = {
  telegram_id: 0,
  language: 'ka',
  subscription_tier: 'free',
  subscription_expires_at: null,
  balance: 0,
  favorites_count: 0,
  created_at: '',
};

interface Patched {
  /** Ответ GET, поверх которого применён PATCH: после reload() свежий GET снова главный */
  base: Me | undefined;
  me: Me;
}

/** Профиль из /api/me. Гостю запрос не отправляется (бэкенд всё равно ответит 401) */
export function useMe() {
  const { isAuthenticated } = useAuth();
  const { data, error, loading, reload } = useApi<Me>(isAuthenticated ? ME_PATH : null);
  const [patched, setPatched] = useState<Patched | null>(null);

  const me = patched && patched.base === data ? patched.me : data;

  /** PATCH /api/me — язык сохраняется на бэкенде (им пользуется и бот) */
  const setLanguage = useCallback(
    async (language: Lang) => {
      const body: UpdateMeRequest = { language };
      const updated = await apiPatch<Me>(ME_PATH, body);
      setPatched({ base: data, me: updated });
    },
    [data],
  );

  return { me, error, loading, reload, setLanguage };
}
