// Единая точка общения с бэкендом: все запросы идут через apiGet/apiPost/apiPatch/apiDelete

import { isSignedOut } from '../lib/session';
import { getInitData } from '../lib/telegram';

export class ApiError extends Error {
  readonly status: number;
  /** Машинный код ошибки из тела ответа, например "payment_required" */
  readonly code?: string;

  constructor(status: number, message: string, code?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  /** 401: бэкенд не узнал пользователя (нет или неверный X-Telegram-Init-Data) */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** 402: исчерпан лимит бесплатного тарифа — нужно предложить Premium */
  get isPaymentRequired(): boolean {
    return this.status === 402 || this.code === 'payment_required';
  }
}

/**
 * Код ошибки из JSON-тела. Бэкенд может положить его в корень ({ code }),
 * в { error: { code } } или в FastAPI-обёртку { detail: { code } }
 */
async function readErrorCode(response: Response): Promise<string | undefined> {
  try {
    const body: unknown = await response.json();
    const candidates = [body, pick(body, 'error'), pick(body, 'detail')];
    for (const candidate of candidates) {
      const code = pick(candidate, 'code');
      if (typeof code === 'string') return code;
    }
  } catch {
    // Тело не JSON или пустое — кода нет
  }
  return undefined;
}

function pick(value: unknown, key: string): unknown {
  return typeof value === 'object' && value !== null
    ? (value as Record<string, unknown>)[key]
    : undefined;
}

async function request<T>(
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
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
    const code = await readErrorCode(response);
    throw new ApiError(response.status, response.statusText || 'Request failed', code);
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

/** Удаление ресурса (обычно ответ 204 без тела) */
export function apiDelete<T = void>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>('DELETE', path, undefined, signal);
}
