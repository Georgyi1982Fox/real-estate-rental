import { useEffect } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import AuthForm from '../components/AuthForm';
import AuthSigningIn from '../components/AuthSigningIn';
import GoogleButton from '../components/GoogleButton';
import LanguageSwitcher from '../components/LanguageSwitcher';
import OpenInTelegram from '../components/OpenInTelegram';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { WEB_AUTH_ENABLED } from '../lib/config';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

// Вход в Telegram мгновенный — экран «Входим…» держим секунду, чтобы анимация успела сыграть
const SIGNING_IN_MS = 1000;

const GUEST_LINK_CLASS =
  'auth-page__guest mx-auto rounded-[var(--radius-md)] px-4 py-3 text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)]';

export default function AuthPage() {
  const { t } = useI18n();
  const { isInTelegram, isAuthenticated, loading, signInWithTelegram } = useAuth();
  const navigate = useNavigate();
  const showToast = useToast();
  const [params] = useSearchParams();
  useDocumentTitle(`${t.auth.page_title} — Bina.ai`);

  // Telegram: пользователь уже известен из initData → mock-токен и на главную
  const autoSignIn = isInTelegram && isAuthenticated;
  useEffect(() => {
    if (!autoSignIn) return;
    signInWithTelegram();
    const timer = window.setTimeout(() => {
      haptic('success');
      navigate('/', { replace: true });
    }, SIGNING_IN_MS);
    return () => window.clearTimeout(timer);
  }, [autoSignIn, signInWithTelegram, navigate]);

  // Браузер: уже есть сессия (в т. ч. после возврата с Google) — на /auth делать нечего
  if (!isInTelegram && !loading && isAuthenticated) return <Navigate to="/" replace />;

  const guestLink = (
    <Link to="/" className={GUEST_LINK_CLASS}>
      {t.auth.continue_guest}
    </Link>
  );

  const renderContent = () => {
    if (autoSignIn) return <AuthSigningIn />;

    if (loading) {
      return (
        <p
          className="auth-page__loading grid place-items-center py-16 text-[var(--primary)]"
          role="status"
        >
          <span className="spinner size-8" aria-hidden="true" />
          <span className="sr-only">{t.listing.loading}</span>
        </p>
      );
    }

    // Telegram после «Выйти»: вход — только по явному нажатию
    if (isInTelegram) {
      return (
        <>
          <OpenInTelegram />
          {guestLink}
        </>
      );
    }

    // Обычный браузер без бэкенда входа: только ссылка на бота
    if (!WEB_AUTH_ENABLED) {
      return (
        <>
          <OpenInTelegram />
          {guestLink}
        </>
      );
    }

    // Обычный браузер: ссылка на бота + Google + email
    return (
      <>
        <OpenInTelegram>
          <p className="auth-divider">{t.auth.or}</p>

          {params.get('error') === 'google' && (
            <p
              className="auth-page__error m-0 rounded-[var(--radius-md)] border border-[var(--danger)] px-4 py-3 text-sm text-[var(--danger)]"
              role="alert"
            >
              {t.auth.google_error}
            </p>
          )}
          <GoogleButton />

          <p className="auth-divider">{t.auth.or}</p>

          <AuthForm
            onSuccess={() => {
              showToast(t.auth.success, 'success');
              navigate('/', { replace: true });
            }}
          />
        </OpenInTelegram>
        {guestLink}
      </>
    );
  };

  return (
    <main className="auth-page flex min-h-dvh flex-col px-4 pb-[calc(1.5rem+var(--safe-bottom))] pt-[calc(0.75rem+var(--safe-top))] sm:px-6">
      {!autoSignIn && (
        <header className="auth-page__top relative z-30 flex justify-end">
          <LanguageSwitcher />
        </header>
      )}
      <section className="auth-page__body mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-4 py-6">
        {renderContent()}
      </section>
    </main>
  );
}
