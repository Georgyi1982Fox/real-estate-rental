import { useId } from 'react';
import type { Me } from '../api/types';
import { fill, formatDate, formatMoney } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

interface SubscriptionCardProps {
  me: Me;
  /** «Улучшить» — только для бесплатного тарифа */
  onUpgrade: () => void;
}

/** Тариф, дата окончания и баланс */
export default function SubscriptionCard({ me, onUpgrade }: SubscriptionCardProps) {
  const { t, lang } = useI18n();
  const pt = t.profile;
  const titleId = useId();
  const isFree = me.subscription_tier === 'free';
  // Неизвестный тариф (бэкенд добавил новый раньше фронтенда) — показываем как есть
  const tierName: string = pt.tiers[me.subscription_tier] ?? me.subscription_tier;
  const expires = me.subscription_expires_at ? formatDate(me.subscription_expires_at, lang) : '';

  return (
    <section
      className="subscription-card flex flex-col gap-4 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)]"
      aria-labelledby={titleId}
    >
      <header className="subscription-card__header flex items-start gap-3">
        <span
          className={`subscription-card__icon inline-grid size-11 shrink-0 place-items-center rounded-full ${isFree ? 'bg-[var(--surface-hover)] text-[var(--text-secondary)]' : 'bg-[var(--accent)]/15 text-[var(--accent)]'}`}
        >
          <Icon name="crown" />
        </span>
        <hgroup className="min-w-0">
          <h2 id={titleId} className="text-sm text-[var(--text-secondary)]">
            {pt.subscription}
          </h2>
          <p className="subscription-card__tier text-xl font-semibold">{tierName}</p>
          {expires && (
            <p className="subscription-card__expires mt-0.5 text-sm text-[var(--text-secondary)]">
              {fill(pt.expires, expires)}
            </p>
          )}
        </hgroup>
      </header>

      <dl className="subscription-card__balance flex items-center justify-between gap-3 border-t border-[var(--border)] pt-4 text-sm">
        <dt className="text-[var(--text-secondary)]">{pt.balance}</dt>
        <dd className="text-base font-semibold">{formatMoney(me.balance)}</dd>
      </dl>

      {isFree && (
        <button
          type="button"
          className="subscription-card__upgrade inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]"
          onClick={onUpgrade}
        >
          <Icon name="crown" className="size-4" />
          {pt.upgrade}
        </button>
      )}
    </section>
  );
}
