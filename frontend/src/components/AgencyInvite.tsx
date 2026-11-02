import { Link } from 'react-router-dom';
import { AGENCY_FREE_LISTINGS, AGENCY_PATH } from '../lib/agency';
import { fill } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

/** Приглашение на «Моих объявлениях»: «Вы риелтор или агентство?» → регистрация в кабинете */
export default function AgencyInvite() {
  const { t } = useI18n();
  const at = t.agency;

  return (
    <Link
      to={AGENCY_PATH}
      className="agency-invite flex items-center gap-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[var(--shadow-sm)] hover:bg-[var(--surface-hover)] active:scale-[.98]"
      onClick={() => haptic('light')}
    >
      <span className="inline-grid size-10 shrink-0 place-items-center rounded-xl bg-[var(--tone-owner)] text-[var(--surface)]">
        <Icon name="briefcase" className="size-5" />
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="text-sm font-semibold leading-tight">{at.invite_title}</span>
        <span className="text-sm leading-snug text-[var(--text-secondary)]">
          {fill(at.invite_text, AGENCY_FREE_LISTINGS)}
        </span>
      </span>
      <Icon name="chevron" className="size-4 shrink-0 text-[var(--text-secondary)]" />
    </Link>
  );
}
