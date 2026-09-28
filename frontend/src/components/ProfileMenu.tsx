import { useCallback, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { BOT_URL } from '../lib/config';
import { haptic, openLink } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import type { IconName } from './Icon';
import Modal from './Modal';
import ProfileSection from './ProfileSection';

const ROW_CLASS =
  'profile-menu__row flex min-h-12 w-full items-center gap-3 px-4 py-3 text-left text-sm font-medium hover:bg-[var(--surface-hover)]';

/** Содержимое строки меню: иконка, текст, шеврон */
function RowContent({ icon, label }: { icon: IconName; label: string }) {
  return (
    <>
      <Icon name={icon} className="size-5 text-[var(--primary)]" />
      <span className="min-w-0 flex-1">{label}</span>
      <Icon name="chevron" className="size-4 text-[var(--text-secondary)]" />
    </>
  );
}

/** Меню профиля: избранное, сохранённые поиски, помощь (бот), о приложении */
export default function ProfileMenu() {
  const { t } = useI18n();
  const pt = t.profile;
  const navigate = useNavigate();
  const [aboutOpen, setAboutOpen] = useState(false);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeAbout = useCallback(() => setAboutOpen(false), []);

  return (
    <>
      <ProfileSection title={pt.menu} as="nav">
        <li>
          <Link to="/favorites" className={ROW_CLASS} onClick={() => haptic('light')}>
            <RowContent icon="heart" label={t.header.favorites} />
          </Link>
        </li>
        <li>
          <Link to="/searches" className={ROW_CLASS} onClick={() => haptic('light')}>
            <RowContent icon="bell" label={t.header.searches} />
          </Link>
        </li>
        <li>
          <a
            href={BOT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className={ROW_CLASS}
            onClick={(event) => {
              // В Telegram чат с ботом открывается нативно (openTelegramLink)
              event.preventDefault();
              haptic('light');
              openLink(BOT_URL, navigate);
            }}
          >
            <RowContent icon="help" label={pt.help} />
          </a>
        </li>
        <li>
          <button
            type="button"
            className={ROW_CLASS}
            aria-haspopup="dialog"
            onClick={() => {
              haptic('light');
              setAboutOpen(true);
            }}
          >
            <RowContent icon="info" label={pt.about} />
          </button>
        </li>
      </ProfileSection>

      <Modal open={aboutOpen} title={pt.about} onClose={closeAbout}>
        <p className="text-sm leading-relaxed">{pt.about_text}</p>
        <p className="mt-4 text-xs text-[var(--text-secondary)]">
          © {new Date().getFullYear()} Bina.ai
        </p>
      </Modal>
    </>
  );
}
