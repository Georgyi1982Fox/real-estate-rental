import { useCallback, useEffect, useState } from 'react';
import { ApiError, apiGet } from '../api/client';

interface ApiState<T> {
  path: string | null;
  data?: T;
  error?: ApiError;
}

export interface ApiResult<T> {
  data: T | undefined;
  error: ApiError | undefined;
  loading: boolean;
  reload: () => void;
}

/**
 * GET-запрос с loading/error состояниями. При смене path старые данные сразу скрываются,
 * незавершённый запрос отменяется. path = null — запрос не выполняется.
 */
export function useApi<T>(path: string | null): ApiResult<T> {
  const [state, setState] = useState<ApiState<T>>({ path: null });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    setState({ path: null });

    apiGet<T>(path, controller.signal).then(
      (data) => setState({ path, data }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setState({ path, error: error instanceof ApiError ? error : new ApiError(0, String(error)) });
      },
    );
    return () => controller.abort();
  }, [path, attempt]);

  const reload = useCallback(() => setAttempt((value) => value + 1), []);
  const settled = path !== null && state.path === path;

  return {
    data: settled ? state.data : undefined,
    error: settled ? state.error : undefined,
    loading: path !== null && !settled,
    reload,
  };
}
