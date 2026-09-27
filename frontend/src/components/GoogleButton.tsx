import { APP_BASE } from '../lib/config';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

// OAuth целиком на бэкенде: уходим на /api/auth/google/login, после Google бэкенд ставит
// cookie-сессию и возвращает на /auth (при ошибке — /auth?error=google)
const GOOGLE_LOGIN_URL = `/api/auth/google/login?return_to=${encodeURIComponent(`${APP_BASE}auth`)}`;

export default function GoogleButton() {
  const { t } = useI18n();

  return (
    <a
      href={GOOGLE_LOGIN_URL}
      className="google-button flex min-h-12 w-full items-center justify-center gap-3 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm font-semibold text-[var(--text-primary)] shadow-[var(--shadow-sm)] hover:bg-[var(--surface-hover)] active:scale-[0.99]"
      onClick={() => haptic('light')}
    >
      {/* Официальный логотип Google «G» — цвета бренда в theme.css (--brand-google-*) */}
      <svg className="google-button__logo size-5 shrink-0" viewBox="0 0 48 48" aria-hidden="true">
        <path
          className="fill-[var(--brand-google-red)]"
          d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
        />
        <path
          className="fill-[var(--brand-google-blue)]"
          d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
        />
        <path
          className="fill-[var(--brand-google-yellow)]"
          d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
        />
        <path
          className="fill-[var(--brand-google-green)]"
          d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
        />
      </svg>
      {t.auth.google}
    </a>
  );
}
