import { Link } from 'react-router-dom';
import type { AgencyBrief } from '../api/types';
import { agencyPagePath } from '../lib/agency';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import AgencyLogo from './AgencyLogo';

interface AgencyLinkProps {
  agency: AgencyBrief;
  className?: string;
}

/** Строка «логотип + название» в объявлении: ведёт на страницу агентства */
export default function AgencyLink({ agency, className = '' }: AgencyLinkProps) {
  const { t } = useI18n();

  return (
    <Link
      to={agencyPagePath(agency.id)}
      className={`agency-link inline-flex min-h-7 max-w-full items-center gap-2 rounded-[var(--radius-sm)] text-sm font-medium text-[var(--text-primary)] hover:underline ${className}`}
      onClick={() => haptic('light')}
    >
      <AgencyLogo url={agency.logo_url} className="size-6 rounded-full" iconClassName="size-3.5" />
      <span className="sr-only">{t.agency.listed_by}: </span>
      <span className="truncate">{agency.name}</span>
    </Link>
  );
}
