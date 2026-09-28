import { useCallback, useEffect, useState } from 'react';
import { ApiError, apiGet } from '../api/client';
import type { Listing } from '../api/types';

// Загруженные квартиры по ID — общий кэш на время сессии (повторный заход на страницу мгновенный)
const cache = new Map<string, Listing | null>();

export interface FavoriteListings {
  /** Квартиры в порядке ids; удалённые с сайта (404) пропускаются */
  listings: Listing[];
  loading: boolean;
  error: ApiError | undefined;
  reload: () => void;
}

/**
 * Квартиры избранного по их ID: каждая — GET /api/listings/{id} (параллельно, с кэшем).
 * Так видны все избранные, сколько бы объявлений ни было в базе, а добавление и удаление
 * отражаются сразу, без повторного запроса списка.
 */
export function useFavoriteListings(ids: string[]): FavoriteListings {
  const [, setVersion] = useState(0);
  const [error, setError] = useState<ApiError>();
  const [attempt, setAttempt] = useState(0);
  const missing = ids.filter((id) => !cache.has(id));
  const missingKey = missing.join(',');

  useEffect(() => {
    if (!missingKey) return;
    const controller = new AbortController();
    setError(undefined);
    Promise.all(
      missingKey.split(',').map(async (id) => {
        try {
          cache.set(
            id,
            await apiGet<Listing>(`/api/listings/${encodeURIComponent(id)}`, controller.signal),
          );
        } catch (err) {
          if (err instanceof ApiError && err.isNotFound) cache.set(id, null);
          else throw err;
        }
      }),
    ).then(
      () => setVersion((version) => version + 1),
      (err: unknown) => {
        if (controller.signal.aborted) return;
        setError(err instanceof ApiError ? err : new ApiError(0, String(err)));
        setVersion((version) => version + 1);
      },
    );
    return () => controller.abort();
  }, [missingKey, attempt]);

  const reload = useCallback(() => setAttempt((value) => value + 1), []);

  const listings = ids
    .map((id) => cache.get(id))
    .filter((listing): listing is Listing => listing != null);
  return { listings, loading: missing.length > 0 && !error, error, reload };
}
