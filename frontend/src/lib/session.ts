// Локальное состояние сессии в localStorage.
// Настоящая авторизация — на бэкенде (initData в Telegram, cookie-сессия в браузере);
// здесь только mock-токен и флаг «вышел из аккаунта».

export type AuthMethod = 'telegram' | 'google' | 'email';

const TOKEN_KEY = 'bina:token';
const SIGNED_OUT_KEY = 'bina:signed_out';

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    // localStorage может быть недоступен (приватный режим)
    return null;
  }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    // см. read()
  }
}

/** Mock-токен: только маркер для UI, никуда не отправляется */
export function saveMockToken(method: AuthMethod): void {
  write(TOKEN_KEY, `mock.${method}.${Date.now()}`);
}

export function clearMockToken(): void {
  write(TOKEN_KEY, null);
}

/**
 * Пользователь Telegram нажал «Выйти»: initData перестаёт уходить на бэкенд,
 * и /auth больше не входит автоматически, пока он сам не нажмёт «Войти через Telegram».
 */
export function isSignedOut(): boolean {
  return read(SIGNED_OUT_KEY) === '1';
}

export function setSignedOut(value: boolean): void {
  write(SIGNED_OUT_KEY, value ? '1' : null);
}
