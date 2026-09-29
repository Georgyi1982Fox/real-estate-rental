import { useId } from 'react';
import { Link } from 'react-router-dom';
import type { Me } from '../api/types';
import { fill, formatDate, formatMoney } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

interface SubscriptionCardProps {
  me: Me;
}

/** Тариф («Бесплатный» / «Premium до …»), баланс и переход на /premium */
export default function SubscriptionCard({ me }: SubscriptionCardProps) {
  const { t, lang } = useI18n();
  const pt = t.profile;
  const titleId = useId();
  const isPremium = me.is_premium;
  // Неизвестный тариф (бэкенд добавил новый раньше фронтенда) — показываем как есть
  const tierName: string = isPremium
    ? t.premium.premium
    : (pt.tiers[me.subscription_tier] ?? me.subscription_tier);
  const expires = me.subscription_expires_at ? formatDate(me.subscription_expires_at, lang) : '';

  return (
    <section
      className="subscription-card flex flex-col gap-4 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)]"
      aria-labelledby={titleId}
    >
      <header className="subscription-card__header flex items-start gap-3">
        <span
          className={`subscription-card__icon inline-grid size-11 shrink-0 place-items-center rounded-full ${isPremium ? 'bg-[var(--accent)]/15 text-[var(--accent)]' : 'bg-[var(--surface-hover)] text-[var(--text-secondary)]'}`}
        >
          <Icon name="crown" />
        </span>
        <hgroup className="min-w-0">
          <h2 id={titleId} className="text-sm text-[var(--text-secondary)]">
            {pt.subscription}
          </h2>
          <p
            className={`subscription-card__tier mt-1 inline-flex rounded-full px-3 py-0.5 text-base font-semibold ${isPremium ? 'subscription-card__tier--premium bg-[var(--accent)]/15' : 'bg-[var(--surface-hover)]'}`}
          >
            {tierName}
          </p>
          {isPremium && expires && (
            <p className="subscription-card__expires mt-1 text-sm text-[var(--text-secondary)]">
              {fill(pt.expires, expires)}
            </p>
          )}
        </hgroup>
      </header>

      <dl className="subscription-card__balance flex items-center justify-between gap-3 border-t border-[var(--border)] pt-4 text-sm">
        <dt className="text-[var(--text-secondary)]">{pt.balance}</dt>
        <dd className="text-base font-semibold">{formatMoney(me.balance)}</dd>
      </dl>

      <Link
        to="/premium"
        className={`subscription-card__upgrade inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] px-5 py-2.5 text-sm font-semibold shadow-[var(--shadow-sm)] transition-colors active:scale-[.98] ${isPremium ? 'border border-[var(--primary)] bg-[var(--surface)] text-[var(--primary)] hover:bg-[var(--surface-hover)]' : 'bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)]'}`}
        onClick={() => haptic('light')}
      >
        <Icon name="crown" className="size-4" />
        {isPremium ? pt.renew : pt.upgrade}
      </Link>
    </section>
  );
}
