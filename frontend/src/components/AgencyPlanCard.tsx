import type { AgencyCabinet } from '../api/types';
import { fill, fillVars, formatDayMonth } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import UsageMeter from './UsageMeter';

interface AgencyPlanCardProps {
  agency: AgencyCabinet;
}

/** Плашка пакета: «Бесплатный · 3 из 10 объявлений»; в режиме тестирования всё бесплатно */
export default function AgencyPlanCard({ agency }: AgencyPlanCardProps) {
  const { lang, t } = useI18n();
  const at = t.agency;
  const paid = agency.plan !== null;
  const title = agency.testing_mode ? at.plan_testing : paid ? at.plan_paid : at.plan_free;
  const until =
    paid && !agency.testing_mode && agency.plan_expires_at
      ? fill(at.plan_until, formatDayMonth(agency.plan_expires_at, lang))
      : '';

  return (
    <section
      className="agency-plan flex flex-col gap-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[var(--shadow-sm)] sm:p-5"
      aria-label={at.plan}
    >
      <header className="flex flex-wrap items-baseline justify-between gap-x-3">
        <h2 className="text-base font-semibold">{title}</h2>
        {until && <p className="m-0 text-xs text-[var(--text-secondary)]">{until}</p>}
      </header>
      <ul className="m-0 list-none p-0">
        <UsageMeter label={at.plan_usage} used={agency.active} limit={agency.limit} />
      </ul>
      {agency.active >= agency.limit && !agency.testing_mode && (
        <p className="m-0 text-sm font-medium text-[var(--text-secondary)]">
          {fillVars(at.plan_full, { limit: agency.limit })}
        </p>
      )}
    </section>
  );
}
