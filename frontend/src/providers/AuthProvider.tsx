import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { apiGet, apiPost } from '../api/client';
import type { AuthResponse, AuthUser, LoginRequest, RegisterRequest } from '../api/types';
import { clearFavorites } from '../hooks/useFavorites';
import {
  clearMockToken,
  isSignedOut as readSignedOut,
  saveMockToken,
  setSignedOut as writeSignedOut,
} from '../lib/session';
import { getTelegramUser, isInTelegram as detectTelegram } from '../lib/telegram';
import { useI18n } from './I18nProvider';

// Авторизация:
// - в Telegram пользователь уже известен из initData (бэкенд проверяет подпись заголовка
//   X-Telegram-Init-Data и сам регистрирует пользователя) — отдельный логин не нужен;
// - в браузере — Google / email через бэкенд (cookie-сессия), пользователь из /api/auth/me.

interface AuthContextValue {
  user: AuthUser | null;
  isInTelegram: boolean;
  isAuthenticated: boolean;
  /** true, пока в браузере не пришёл ответ /api/auth/me (в Telegram — сразу false) */
  loading: boolean;
  signInWithTelegram: () => void;
  signIn: (data: LoginRequest) => Promise<void>;
  signUp: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// Вне Telegram SDK не появляется на лету — достаточно проверить один раз
const IN_TELEGRAM = detectTelegram();

interface AuthProviderProps {
  children: ReactNode;
  /** Переход на /auth после выхода (роутер живёт ниже провайдера, см. App.tsx) */
  onLogout: () => void;
}

export function AuthProvider({ children, onLogout }: AuthProviderProps) {
  const { resetLang } = useI18n();
  const [signedOut, setSignedOut] = useState(readSignedOut);
  const [browserUser, setBrowserUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(!IN_TELEGRAM);

  // Браузер: есть ли уже сессия (например, после возврата с Google). 401/нет API — гость
  useEffect(() => {
    if (IN_TELEGRAM) return;
    const controller = new AbortController();
    apiGet<AuthResponse>('/api/auth/me', controller.signal)
      .then(({ user }) => setBrowserUser(user))
      .catch(() => undefined)
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const signInWithTelegram = useCallback(() => {
    if (!IN_TELEGRAM) return;
    writeSignedOut(false);
    setSignedOut(false);
    saveMockToken('telegram');
  }, []);

  const signIn = useCallback(async (data: LoginRequest) => {
    const { user } = await apiPost<AuthResponse>('/api/auth/login', data);
    saveMockToken('email');
    setBrowserUser(user);
  }, []);

  const signUp = useCallback(async (data: RegisterRequest) => {
    const { user } = await apiPost<AuthResponse>('/api/auth/register', data);
    saveMockToken('email');
    setBrowserUser(user);
  }, []);

  const logout = useCallback(() => {
    // Сессию на бэкенде закрываем «в фоне»: локальный выход не должен зависеть от сети
    if (!IN_TELEGRAM) void apiPost('/api/auth/logout').catch(() => undefined);
    clearMockToken();
    clearFavorites();
    resetLang();
    if (IN_TELEGRAM) {
      writeSignedOut(true);
      setSignedOut(true);
    }
    setBrowserUser(null);
    onLogout();
  }, [onLogout, resetLang]);

  const user = IN_TELEGRAM ? (signedOut ? null : getTelegramUser()) : browserUser;

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isInTelegram: IN_TELEGRAM,
      isAuthenticated: user !== null,
      loading,
      signInWithTelegram,
      signIn,
      signUp,
      logout,
    }),
    [user, loading, signInWithTelegram, signIn, signUp, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>');
  return context;
}
