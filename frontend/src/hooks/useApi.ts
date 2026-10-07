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

interface ApiOptions {
  /**
   * Помнить последние ответы до перезагрузки страницы: вернулись на тот же адрес («Назад»
   * из объявления) — данные показываются сразу, без скелетонов, и прокрутка встаёт на место.
   * Запрос всё равно уходит и тихо обновляет показанное.
   */
  remember?: boolean;
}

/** Столько ответов помним; самый старый вытесняется */
const REMEMBER_MAX = 20;
const remembered = new Map<string, unknown>();

function rememberResponse(path: string, data: unknown): void {
  remembered.delete(path);
  remembered.set(path, data);
  const oldest = remembered.keys().next();
  if (remembered.size > REMEMBER_MAX && !oldest.done) remembered.delete(oldest.value);
}

/** Запомненный ответ для path; тип ответа знает вызывающий — тот же, что у запроса */
function recall<T>(path: string | null, enabled: boolean): ApiState<T> {
  if (!enabled || path === null || !remembered.has(path)) return { path: null };
  return { path, data: remembered.get(path) as T };
}

/**
 * GET-запрос с loading/error состояниями. При смене path старые данные сразу скрываются,
 * незавершённый запрос отменяется. path = null — запрос не выполняется.
 */
export function useApi<T>(
  path: string | null,
  { remember = false }: ApiOptions = {},
): ApiResult<T> {
  const [state, setState] = useState<ApiState<T>>(() => recall<T>(path, remember));
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    const known = recall<T>(path, remember);
    setState(known);

    apiGet<T>(path, controller.signal).then(
      (data) => {
        if (remember) rememberResponse(path, data);
        setState({ path, data });
      },
      (error: unknown) => {
        // Обновить не вышло — запомненные данные остаются на экране
        if (controller.signal.aborted || known.path !== null) return;
        setState({
          path,
          error: error instanceof ApiError ? error : new ApiError(0, String(error)),
        });
      },
    );
    return () => controller.abort();
  }, [path, attempt, remember]);

  const reload = useCallback(() => setAttempt((value) => value + 1), []);
  // path только что сменился, эффект ещё не отработал — запомненный ответ нужен уже в этом
  // рендере, иначе на кадр мелькнут скелетоны и прокрутка не восстановится
  const shown = state.path === path ? state : recall<T>(path, remember);
  const settled = path !== null && shown.path === path;

  return {
    data: settled ? shown.data : undefined,
    error: settled ? shown.error : undefined,
    loading: path !== null && !settled,
    reload,
  };
}
