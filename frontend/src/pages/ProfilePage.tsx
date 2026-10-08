import ErrorState from '../components/ErrorState';
import Icon from '../components/Icon';
import OpenInTelegram from '../components/OpenInTelegram';
import ProfileHeader from '../components/ProfileHeader';
import ProfileMenu from '../components/ProfileMenu';
import ProfileSettings from '../components/ProfileSettings';
import ProfileSkeleton from '../components/ProfileSkeleton';
import StatTile from '../components/StatTile';
import SubscriptionCard from '../components/SubscriptionCard';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { FALLBACK_ME, useMe } from '../hooks/useMe';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { STRINGS } from '../i18n/strings';
import type { Lang } from '../i18n/strings';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

const PAGE_CLASS = 'profile mx-auto flex w-full max-w-2xl flex-col gap-6 py-2 sm:py-4';

export default function ProfilePage() {
  const { t, lang, setLang } = useI18n();
  const pt = t.profile;
  const { user, loading: authLoading, logout } = useAuth();
  const { me, error, loading, reload, setLanguage } = useMe();
  const showToast = useToast();

  useDocumentTitle(`${pt.page_title} — bina.ai`);
  useTelegramBackButton('/');

  const logoutButton = (
    <button
      type="button"
      className="profile__logout inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] px-5 py-3 text-sm font-semibold text-[var(--danger)] shadow-[var(--shadow-sm)] hover:bg-[var(--surface-hover)] active:scale-[.98]"
      onClick={() => {
        haptic('medium');
        logout();
      }}
    >
      <Icon name="logout" />
      {pt.logout}
    </button>
  );

  if (authLoading) {
    return (
      <section className={PAGE_CLASS} aria-busy="true">
        <ProfileSkeleton withHeader />
      </section>
    );
  }

  // Гость, Telegram после «Выйти» или 401 от бэкенда (вне Telegram initData нет) — нужен Telegram
  if (!user || error?.isUnauthorized) {
    return (
      <section className="profile profile--guest mx-auto flex w-full max-w-sm flex-col gap-4 py-6">
        <OpenInTelegram />
        {user && logoutButton}
      </section>
    );
  }

  // /api/me не ответил (сеть, 5xx) — показываем данные по умолчанию и плашку «Повторить»
  const profile = me ?? (error ? FALLBACK_ME : undefined);

  const changeLanguage = (code: Lang) => {
    if (code === lang) return;
    haptic('selection');
    // Интерфейс меняется сразу, на бэкенд (для бота) язык уходит в фоне
    setLang(code);
    setLanguage(code).catch(() => showToast(STRINGS[code].profile.language_error, 'error'));
  };

  return (
    <section className={PAGE_CLASS} aria-busy={loading}>
      <ProfileHeader user={user} />

      {error && <ErrorState compact text={pt.fallback} onRetry={reload} />}

      {profile ? (
        <>
          <section className="profile__stats" aria-labelledby="profile-stats-title">
            <h2 id="profile-stats-title" className="sr-only">
              {pt.stats}
            </h2>
            <ul className="grid grid-cols-2 gap-3">
              <li>
                <StatTile
                  icon="heart"
                  label={pt.favorites}
                  value={profile.favorites_count}
                  to="/favorites"
                />
              </li>
              <li>
                {/* Бэкенд просмотры пока не считает — отдельная задача */}
                <StatTile icon="eye" label={pt.viewed} value="—" hint={pt.viewed_soon} />
              </li>
            </ul>
          </section>
          <SubscriptionCard me={profile} />
        </>
      ) : (
        <ProfileSkeleton />
      )}

      <ProfileSettings onLanguageChange={changeLanguage} />
      <ProfileMenu />
      {logoutButton}
    </section>
  );
}
