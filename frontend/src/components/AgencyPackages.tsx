import type { AgencyCabinet } from '../api/types';
import { botSectionUrl } from '../lib/config';
import { fillVars } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import { MY_CARD_ACTION_CLASS } from './MyHotelCard';
import SignLink from './SignLink';

const CARD_CLASS =
  'flex min-w-0 flex-col gap-1 rounded-[var(--radius-md)] border border-[var(--border)] p-3';

interface AgencyPackagesProps {
  agency: AgencyCabinet;
}

/** Пакеты объявлений и Premium-объявление; оплата звёздами — в боте */
export default function AgencyPackages({ agency }: AgencyPackagesProps) {
  const { t } = useI18n();
  const at = t.agency;

  return (
    <section
      className="agency-packages flex flex-col gap-3"
      aria-labelledby="agency-packages-title"
    >
      <h2 id="agency-packages-title" className="text-lg font-semibold">
        {at.packages_title}
      </h2>
      <ul className="m-0 grid list-none grid-cols-1 gap-3 p-0 sm:grid-cols-2">
        {agency.plans.map((plan) => (
          <li
            key={plan.id}
            className={`${CARD_CLASS} ${plan.id === agency.plan ? 'border-[var(--primary)]' : ''} bg-[var(--surface)]`}
          >
            <p className="m-0 text-base font-semibold">
              {fillVars(at.package_listings, { n: plan.listings })}
            </p>
            <p className="m-0 text-sm text-[var(--text-secondary)]">
              {fillVars(at.package_price, { price: plan.price_stars, days: plan.days })}
            </p>
          </li>
        ))}
        <li className={`${CARD_CLASS} bg-[var(--promo-bg)] text-[var(--promo-text)]`}>
          <p className="m-0 inline-flex items-center gap-1.5 text-base font-semibold">
            <Icon name="star" className="size-4" />
            {at.premium_title}
          </p>
          <p className="m-0 text-sm">
            {fillVars(at.package_price, {
              price: agency.bump_price_stars,
              days: agency.bump_days,
            })}
          </p>
          <p className="m-0 text-sm">{at.premium_text}</p>
        </li>
      </ul>
      <SignLink url={botSectionUrl('owner')} className={MY_CARD_ACTION_CLASS}>
        {at.packages_button}
      </SignLink>
      <p className="m-0 text-xs text-[var(--text-secondary)]">{at.pay_hint}</p>
    </section>
  );
}
