// Локальное состояние сессии в localStorage.
// Настоящая авторизация — на бэкенде (initData в Telegram, cookie-сессия в браузере);
// здесь только отметка «вошёл» и флаг «вышел из аккаунта».

import { getInitData } from './telegram';

export type AuthMethod = 'telegram' | 'google' | 'email';

const SIGNED_IN_KEY = 'bina:token';
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

/** Отметка «вошёл» (как и когда): только для интерфейса, никуда не отправляется */
export function markSignedIn(method: AuthMethod): void {
  write(SIGNED_IN_KEY, `${method}.${Date.now()}`);
}

export function clearSignedIn(): void {
  write(SIGNED_IN_KEY, null);
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

/**
 * Пользователь Telegram, который не нажал «Выйти»: избранное и заметки к нему живут
 * на сервере. Гость в браузере хранит избранное только на устройстве, заметок у него нет
 */
export function usesServerFavorites(): boolean {
  return getInitData() !== '' && !isSignedOut();
}
