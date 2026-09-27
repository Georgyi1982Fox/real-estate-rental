import { useId } from 'react';
import { useNotifications } from '../hooks/useNotifications';
import { LANGUAGES } from '../i18n/strings';
import type { Lang } from '../i18n/strings';
import { useI18n } from '../providers/I18nProvider';
import ProfileSection from './ProfileSection';
import Switch from './Switch';

interface ProfileSettingsProps {
  onLanguageChange: (lang: Lang) => void;
}

/** Настройки: язык (ka/ru/en) и уведомления */
export default function ProfileSettings({ onLanguageChange }: ProfileSettingsProps) {
  const { t, lang } = useI18n();
  const pt = t.profile;
  const [notifications, setNotifications] = useNotifications();
  const languageId = useId();

  return (
    <ProfileSection title={pt.settings}>
      <li className="profile-settings__language flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <span id={languageId} className="text-sm font-medium">
          {pt.language}
        </span>
        <span
          className="profile-settings__languages grid grid-cols-3 gap-1 rounded-[var(--radius-md)] bg-[var(--surface-hover)] p-1 sm:min-w-80"
          role="group"
          aria-labelledby={languageId}
        >
          {LANGUAGES.map(({ code, label }) => {
            const active = code === lang;
            return (
              <button
                key={code}
                type="button"
                lang={code}
                aria-pressed={active}
                className={`min-h-10 truncate rounded-[var(--radius-sm)] px-2 text-sm transition-colors duration-200 ${active ? 'bg-[var(--surface)] font-semibold text-[var(--primary)] shadow-[var(--shadow-sm)]' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
                onClick={() => onLanguageChange(code)}
              >
                {label}
              </button>
            );
          })}
        </span>
      </li>
      <li>
        <Switch label={pt.notifications} checked={notifications} onChange={setNotifications} />
      </li>
    </ProfileSection>
  );
}
