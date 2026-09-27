import { useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError } from '../api/client';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import FormField from './FormField';

type Mode = 'login' | 'register';

const MIN_PASSWORD_LENGTH = 8;

interface AuthFormProps {
  /** Успешный вход или регистрация */
  onSuccess: () => void;
}

/** Классический вход / регистрация по email и паролю (сессия — на бэкенде) */
export default function AuthForm({ onSuccess }: AuthFormProps) {
  const { t } = useI18n();
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState<Mode>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const isRegister = mode === 'register';

  const switchMode = (next: Mode) => {
    if (next === mode) return;
    haptic('selection');
    setMode(next);
    setError(null);
  };

  // Ошибки бэкенда → понятный текст; остальное (сеть, 5xx) — общее сообщение
  const describe = (reason: unknown): string => {
    if (reason instanceof ApiError) {
      if (reason.status === 401) return t.auth.error_credentials;
      if (reason.status === 409) return t.auth.error_exists;
    }
    return t.auth.error_generic;
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) return;
    if (isRegister && password.length < MIN_PASSWORD_LENGTH) {
      setError(t.auth.error_short);
      return;
    }
    if (isRegister && password !== confirm) {
      setError(t.auth.error_mismatch);
      return;
    }

    setError(null);
    setPending(true);
    try {
      const credentials = { email: email.trim(), password };
      if (isRegister) await signUp({ ...credentials, first_name: name.trim() });
      else await signIn(credentials);
      haptic('success');
      onSuccess();
    } catch (reason) {
      setError(describe(reason));
      haptic('error');
      setPending(false);
    }
  };

  const tabClass = (active: boolean) =>
    `auth-form__tab min-h-10 flex-1 rounded-[var(--radius-sm)] px-3 text-sm font-semibold transition-colors duration-200 ${active ? 'bg-[var(--surface)] text-[var(--text-primary)] shadow-[var(--shadow-sm)]' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`;

  return (
    <section className="auth-form flex flex-col gap-4">
      {/* Переключатель режима — группа кнопок, а не навигация */}
      <div
        role="group"
        aria-label={t.auth.mode}
        className="auth-form__tabs flex gap-1 rounded-[var(--radius-md)] bg-[var(--surface-hover)] p-1"
      >
        <button
          type="button"
          className={tabClass(!isRegister)}
          aria-pressed={!isRegister}
          onClick={() => switchMode('login')}
        >
          {t.auth.tab_login}
        </button>
        <button
          type="button"
          className={tabClass(isRegister)}
          aria-pressed={isRegister}
          onClick={() => switchMode('register')}
        >
          {t.auth.tab_register}
        </button>
      </div>

      <form className="auth-form__form flex flex-col gap-4" onSubmit={handleSubmit}>
        {isRegister && (
          <FormField
            label={t.auth.name}
            name="first_name"
            autoComplete="given-name"
            required
            maxLength={64}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        )}
        <FormField
          label={t.auth.email}
          type="email"
          name="email"
          autoComplete="email"
          inputMode="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <FormField
          label={t.auth.password}
          type="password"
          name="password"
          autoComplete={isRegister ? 'new-password' : 'current-password'}
          required
          minLength={isRegister ? MIN_PASSWORD_LENGTH : undefined}
          hint={isRegister ? t.auth.password_hint : undefined}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        {isRegister && (
          <FormField
            label={t.auth.password_confirm}
            type="password"
            name="password_confirm"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
          />
        )}

        {error && (
          <p
            className="auth-form__error m-0 rounded-[var(--radius-md)] border border-[var(--danger)] px-4 py-3 text-sm text-[var(--danger)]"
            role="alert"
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          className="auth-form__submit inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-3 text-sm font-semibold text-white shadow-[var(--shadow-sm)] hover:bg-[var(--primary-hover)] active:scale-[0.99] disabled:opacity-70"
          disabled={pending}
          aria-busy={pending}
        >
          {pending && <span className="spinner" aria-hidden="true" />}
          {isRegister ? t.auth.submit_register : t.auth.submit_login}
        </button>
      </form>
    </section>
  );
}
