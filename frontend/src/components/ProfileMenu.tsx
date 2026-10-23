import { Link } from 'react-router-dom';
import { HISTORY_PATH } from '../lib/history';
import { INVITE_PATH } from '../lib/referral';
import { DOCUMENTS_PATH } from '../lib/signing';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import type { IconName } from './Icon';
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

/**
 * Меню профиля — только своё: избранное, недавно смотрели, сохранённые поиски, мои документы,
 * пригласить друга.
 * Помощь, поддержка, «О приложении», акт приёмки, Premium и документы сервиса — в «Ещё»
 */
export default function ProfileMenu() {
  const { t } = useI18n();
  const pt = t.profile;
  const rows: { to: string; icon: IconName; label: string }[] = [
    { to: '/favorites', icon: 'heart', label: t.header.favorites },
    { to: HISTORY_PATH, icon: 'clock', label: t.history.title },
    { to: '/searches', icon: 'bell', label: t.header.searches },
    { to: DOCUMENTS_PATH, icon: 'file', label: t.signing.title },
    { to: INVITE_PATH, icon: 'gift', label: t.hub.tiles.invite.title },
  ];

  return (
    <ProfileSection title={pt.menu} as="nav">
      {rows.map((row) => (
        <li key={row.to}>
          <Link to={row.to} className={ROW_CLASS} onClick={() => haptic('light')}>
            <RowContent icon={row.icon} label={row.label} />
          </Link>
        </li>
      ))}
    </ProfileSection>
  );
}
