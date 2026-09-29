import { useId } from 'react';
import type { Plan, SubscriptionLimits } from '../api/types';
import { fill, fillVars } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';

interface PlanComparisonProps {
  free: SubscriptionLimits;
  premium: SubscriptionLimits;
  plan: Plan;
  /** Подсветить колонку текущего тарифа; undefined — тариф неизвестен (гость) */
  isPremium?: boolean;
}

const CELL = 'px-3 py-3 align-top sm:px-4';

/** Таблица «Бесплатно / Premium»: лимиты избранного, сохранённых поисков и цена */
export default function PlanComparison({ free, premium, plan, isPremium }: PlanComparisonProps) {
  const { t } = useI18n();
  const pt = t.premium;
  const titleId = useId();

  /** null — без ограничения; 1 — просто «1»; больше — «до N» */
  const limitText = (limit: number | null) => {
    if (limit === null) return pt.unlimited;
    return limit <= 1 ? String(limit) : fill(pt.up_to, limit);
  };

  const rows = [
    { label: pt.favorites, free: limitText(free.favorites), premium: limitText(premium.favorites) },
    { label: pt.searches, free: limitText(free.searches), premium: limitText(premium.searches) },
    {
      label: pt.price,
      free: '—',
      premium: fillVars(pt.price_value, { price: plan.price_stars, days: plan.days }),
    },
  ];

  const columnHead = (name: string, current: boolean) => (
    <>
      <span className="block">{name}</span>
      {current && (
        <span className="plan-comparison__current mt-1 inline-block rounded-full bg-[var(--surface-hover)] px-2 py-0.5 text-xs font-medium text-[var(--text-secondary)]">
          {pt.current_plan}
        </span>
      )}
    </>
  );

  return (
    <section
      className="plan-comparison overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)]"
      aria-labelledby={titleId}
    >
      <h2 id={titleId} className="px-4 pb-1 pt-4 text-lg font-semibold sm:px-5">
        {pt.compare}
      </h2>
      <table className="plan-comparison__table w-full border-collapse text-sm">
        <thead>
          <tr className="text-left">
            <th scope="col" className={`${CELL} font-medium text-[var(--text-secondary)]`}>
              <span className="sr-only">{pt.feature}</span>
            </th>
            <th scope="col" className={`${CELL} font-semibold`}>
              {columnHead(pt.free, isPremium === false)}
            </th>
            <th
              scope="col"
              className={`${CELL} plan-comparison__premium bg-[var(--accent)]/10 font-semibold text-[var(--text-primary)]`}
            >
              {columnHead(pt.premium, isPremium === true)}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label} className="border-t border-[var(--border)]">
              <th
                scope="row"
                className={`${CELL} text-left font-medium text-[var(--text-secondary)]`}
              >
                {row.label}
              </th>
              <td className={`${CELL} whitespace-nowrap`}>{row.free}</td>
              <td
                className={`${CELL} plan-comparison__premium bg-[var(--accent)]/10 font-semibold`}
              >
                {row.premium}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
