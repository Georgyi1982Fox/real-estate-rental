import { useId, type ReactNode } from 'react';
import type { Plan, SubscriptionLimits } from '../api/types';
import { fill, fillVars, plural } from '../lib/format';
import { FREE_NOTIFY_DELAY_HOURS } from '../lib/premium';
import { useI18n } from '../providers/I18nProvider';

interface PlanComparisonProps {
  free: SubscriptionLimits;
  premium: SubscriptionLimits;
  /** Тарифы от короткого к длинному — все попадают в строку «Цена» */
  plans: Plan[];
  /** Подсветить колонку текущего тарифа; undefined — тариф неизвестен (гость) */
  isPremium?: boolean;
}

const CELL = 'px-3 py-3 align-top sm:px-4';

interface Row {
  label: string;
  free: ReactNode;
  premium: ReactNode;
}

/** Таблица «Бесплатно / Premium»: лимиты, уведомления и цена */
export default function PlanComparison({ free, premium, plans, isPremium }: PlanComparisonProps) {
  const { t, lang } = useI18n();
  const pt = t.premium;
  const titleId = useId();

  /** null — без ограничения; 1 — просто «1»; больше — «до N» */
  const limitText = (limit: number | null) => {
    if (limit === null) return pt.unlimited;
    return limit <= 1 ? String(limit) : fill(pt.up_to, limit);
  };

  const rows: Row[] = [
    { label: pt.favorites, free: limitText(free.favorites), premium: limitText(premium.favorites) },
    { label: pt.searches, free: limitText(free.searches), premium: limitText(premium.searches) },
    {
      label: pt.notify_new,
      free: fill(pt.notify_delay, FREE_NOTIFY_DELAY_HOURS),
      premium: pt.notify_instant,
    },
    { label: pt.price_drop, free: '—', premium: '✓' },
    {
      label: pt.price,
      free: '—',
      // Каждый тариф с новой строки: колонка узкая, «100 ⭐ / 7 дней · 250 ⭐ / 30 дней» не влезет
      premium: plans.map((plan) => (
        <span key={plan.id} className="plan-comparison__price block [&+&]:mt-1.5">
          {fillVars(pt.price_value, {
            price: plan.price_stars,
            days: plural(pt.days, plan.days, lang),
          })}
        </span>
      )),
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
      {/* Фиксированные колонки: ширина не зависит от длины перевода, «Бесплатно» = «Premium» */}
      <table className="plan-comparison__table w-full table-fixed border-collapse text-sm">
        <colgroup>
          <col className="w-[36%]" />
          <col className="w-[32%]" />
          <col className="w-[32%]" />
        </colgroup>
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
                // 13px на телефоне: длинные грузинские слова иначе рвутся посреди слова
                className={`${CELL} text-left text-[13px] font-medium text-[var(--text-secondary)] sm:text-sm`}
              >
                {row.label}
              </th>
              <td className={CELL}>{row.free}</td>
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
