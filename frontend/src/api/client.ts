// Единая точка общения с бэкендом: все запросы идут через apiGet/apiPost

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
}

async function request<T>(method: 'GET' | 'POST', path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      signal,
      headers: { Accept: 'application/json' },
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
  return (await response.json()) as T;
}

export function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>('GET', path, signal);
}

export function apiPost<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>('POST', path, signal);
}
