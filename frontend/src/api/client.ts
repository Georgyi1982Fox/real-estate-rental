// Единая точка общения с бэкендом: все запросы идут через apiGet/apiPost/apiPatch/apiDelete

import { isSignedOut } from '../lib/session';
import { getInitData } from '../lib/telegram';

export class ApiError extends Error {
  readonly status: number;
  /** Машинный код ошибки из тела ответа, например "payment_required" */
  readonly code?: string;
  /** Текст ошибки из тела ответа (FastAPI: { detail: "rejected: bad_price" }) */
  readonly detail?: string;

  constructor(status: number, message: string, code?: string, detail?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.detail = detail;
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
 * Код и текст ошибки из JSON-тела. Код бэкенд может положить в корень ({ code }),
 * в { error: { code } } или в FastAPI-обёртку { detail: { code } }; текст — строка detail
 */
async function readError(response: Response): Promise<{ code?: string; detail?: string }> {
  try {
    const body: unknown = await response.json();
    const rawDetail = pick(body, 'detail');
    const detail = typeof rawDetail === 'string' ? rawDetail : undefined;
    const candidates = [body, pick(body, 'error'), rawDetail];
    for (const candidate of candidates) {
      const code = pick(candidate, 'code');
      if (typeof code === 'string') return { code, detail };
    }
    return { detail };
  } catch {
    // Тело не JSON или пустое — ни кода, ни текста
  }
  return {};
}

function pick(value: unknown, key: string): unknown {
  return typeof value === 'object' && value !== null
    ? (value as Record<string, unknown>)[key]
    : undefined;
}

async function request<T>(
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  // Внутри Telegram бэкенд проверяет подпись initData и по ней узнаёт пользователя.
  // После «Выйти» запросы идут анонимно, пока пользователь снова не войдёт
  const initData = isSignedOut() ? '' : getInitData();
  if (initData) headers['X-Telegram-Init-Data'] = initData;
  // Файл уходит телом запроса как есть, всё остальное — JSON
  const file = body instanceof Blob ? body : null;
  if (file) headers['Content-Type'] = file.type || 'application/octet-stream';
  else if (body !== undefined) headers['Content-Type'] = 'application/json';

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      signal,
      headers,
      body: file ?? (body === undefined ? undefined : JSON.stringify(body)),
      credentials: 'same-origin',
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    // Сеть недоступна — status 0
    throw new ApiError(0, 'Network error');
  }

  if (!response.ok) {
    const { code, detail } = await readError(response);
    throw new ApiError(response.status, response.statusText || 'Request failed', code, detail);
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

/** Замена ресурса целиком, body сериализуется в JSON */
export function apiPut<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>('PUT', path, body, signal);
}

/** Загрузка файла: тело запроса — сам файл (например, фото гостиницы) */
export function apiUpload<T>(path: string, file: Blob, signal?: AbortSignal): Promise<T> {
  return request<T>('POST', path, file, signal);
}

/** Удаление ресурса (обычно ответ 204 без тела) */
export function apiDelete<T = void>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>('DELETE', path, undefined, signal);
}
