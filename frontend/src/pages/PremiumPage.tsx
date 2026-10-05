import { useState } from 'react';
import ErrorState from '../components/ErrorState';
import Icon from '../components/Icon';
import OpenInTelegram from '../components/OpenInTelegram';
import PlanComparison from '../components/PlanComparison';
import PlanPicker from '../components/PlanPicker';
import UsageMeter from '../components/UsageMeter';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useSubscription } from '../hooks/useSubscription';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { useTelegramMainButton } from '../hooks/useTelegramMainButton';
import { fill, formatDate } from '../lib/format';
import { FREE_LIMITS, PREMIUM_LIMITS, premiumPlans } from '../lib/premium';
import { canPay, isInTelegram } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

const CARD_CLASS =
  'rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)]';

export default function PremiumPage() {
  const { t, lang } = useI18n();
  const pt = t.premium;
  const { subscription, loading, error, unauthorized, reload, buy, buying } = useSubscription();

  useDocumentTitle(`${pt.page_title} — Bina.ai`);
  useTelegramBackButton('/profile');

  const plans = premiumPlans(subscription?.plans);
  const [selectedId, setSelectedId] = useState<string>();
  // Пока пользователь не выбрал сам — самый короткий тариф (7 дней)
  const plan = plans.find((item) => item.id === selectedId) ?? plans[0];
  const isPremium = subscription?.is_premium;
  // Бэкенд отдаёт лимиты только текущего тарифа — вторая колонка из констант
  const freeLimits = isPremium === false && subscription ? subscription.limits : FREE_LIMITS;
  const premiumLimits = isPremium && subscription ? subscription.limits : PREMIUM_LIMITS;
  const expires = subscription?.expires_at ? formatDate(subscription.expires_at, lang) : '';
  const payable = !unauthorized && canPay();
  const buyText = buying
    ? pt.paying
    : fill(isPremium ? pt.renew : pt.buy, plan?.price_stars ?? '');
  const startPurchase = () => {
    if (plan) void buy(plan.id);
  };

  // В Telegram «Купить» — нативная MainButton внизу экрана, в браузере платить нельзя
  const nativeBuy = useTelegramMainButton({
    text: buyText,
    onClick: startPurchase,
    visible: payable && subscription !== undefined && plan !== undefined,
    loading: buying,
  });

  let action;
  if (unauthorized || !isInTelegram()) {
    // Гость, вход через Google/email или «Выйти» в Telegram — оплата звёздами только в Telegram
    action = (
      <article className={`premium__telegram ${CARD_CLASS}`}>
        <OpenInTelegram plain />
      </article>
    );
  } else if (!payable) {
    action = (
      <p className="premium__update rounded-[var(--radius-md)] bg-[var(--surface-hover)] p-4 text-center text-sm">
        {pt.update_telegram}
      </p>
    );
  } else if (!nativeBuy && subscription && plan) {
    action = (
      <button
        type="button"
        className="premium__buy inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-3 text-base font-semibold text-white shadow-[var(--shadow-md)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98] disabled:opacity-70"
        disabled={buying}
        aria-busy={buying}
        onClick={startPurchase}
      >
        {buying ? <span className="spinner" aria-hidden="true" /> : <Icon name="crown" />}
        {buyText}
      </button>
    );
  }

  return (
    <section
      className="premium mx-auto flex w-full max-w-2xl flex-col gap-6 py-2 sm:py-4"
      aria-busy={loading || buying}
    >
      <header className="premium__hero flex flex-col items-center gap-3 pt-2 text-center">
        <span className="premium__badge medallion inline-grid size-20 place-items-center rounded-full bg-[var(--accent)]/15 text-[var(--accent)] shadow-[var(--shadow-md)]">
          <Icon name="crown" className="size-10" />
        </span>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{pt.title}</h1>
        <p className="max-w-md text-sm text-[var(--text-secondary)] sm:text-base">{pt.subtitle}</p>
        {isPremium && expires && (
          <p className="premium__status inline-flex items-center gap-2 rounded-full bg-[var(--secondary)]/15 px-3 py-1 text-sm font-semibold text-[var(--text-primary)]">
            <Icon name="check" className="size-4 text-[var(--secondary)]" />
            {fill(pt.active_until, expires)}
          </p>
        )}
      </header>

      {error && <ErrorState compact onRetry={reload} />}

      <PlanComparison
        free={freeLimits}
        premium={premiumLimits}
        plans={plans}
        isPremium={isPremium}
      />

      {!unauthorized && (loading || subscription) && (
        <section className={`premium__usage ${CARD_CLASS}`} aria-labelledby="premium-usage-title">
          <h2 id="premium-usage-title" className="mb-4 text-lg font-semibold">
            {pt.usage}
          </h2>
          {subscription ? (
            <ul className="flex flex-col gap-4">
              <UsageMeter
                label={pt.favorites}
                used={subscription.usage.favorites}
                limit={subscription.limits.favorites}
              />
              <UsageMeter
                label={pt.searches}
                used={subscription.usage.searches}
                limit={subscription.limits.searches}
              />
            </ul>
          ) : (
            <ul className="flex animate-pulse flex-col gap-4" aria-hidden="true">
              {[0, 1].map((index) => (
                <li key={index} className="flex flex-col gap-2">
                  <span className="h-4 w-2/3 rounded bg-[var(--surface-hover)]" />
                  <span className="h-2 w-full rounded-full bg-[var(--surface-hover)]" />
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {payable && subscription && plan && (
        <PlanPicker
          plans={plans}
          selectedId={plan.id}
          onSelect={setSelectedId}
          disabled={buying}
        />
      )}

      {action}
    </section>
  );
}
