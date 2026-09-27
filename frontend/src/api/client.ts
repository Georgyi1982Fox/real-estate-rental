// Единая точка общения с бэкендом: все запросы идут через apiGet/apiPost/apiPatch

import { isSignedOut } from '../lib/session';
import { getInitData } from '../lib/telegram';

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  /** 401: бэкенд не узнал пользователя (нет или неверный X-Telegram-Init-Data) */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }
}

async function request<T>(
  method: 'GET' | 'POST' | 'PATCH',
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  // Внутри Telegram бэкенд проверяет подпись initData и по ней узнаёт пользователя.
  // После «Выйти» запросы идут анонимно, пока пользователь снова не войдёт
  const initData = isSignedOut() ? '' : getInitData();
  if (initData) headers['X-Telegram-Init-Data'] = initData;
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      signal,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'same-origin',
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    // Сеть недоступна — status 0
    throw new ApiError(0, 'Network error');
  }

  if (!response.ok) {
    throw new ApiError(response.status, response.statusText || 'Request failed');
  }
  // 204 No Content (например, /api/auth/logout)
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>('GET', path, undefined, signal);
}

/** body сериализуется в JSON */
export function apiPost<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>('POST', path, body, signal);
}

/** Частичное обновление ресурса, body сериализуется в JSON */
export function apiPatch<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>('PATCH', path, body, signal);
}
