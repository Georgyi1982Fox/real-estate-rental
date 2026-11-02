import { Link } from 'react-router-dom';
import type { AgencyListingStats } from '../api/types';
import { botSectionUrl } from '../lib/config';
import { fill, formatDayMonth, tr } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import type { IconName } from './Icon';
import ListingPrice from './ListingPrice';
import { MY_CARD_ACTION_CLASS, MY_CARD_STATUS_CLASS } from './MyHotelCard';
import SignLink from './SignLink';

interface AgencyListingCardProps {
  item: AgencyListingStats;
  /** Заблокированному кабинету платить не за что */
  blocked: boolean;
}

/** Объявление в кабинете: цифры за 30 дней, значок Premium и кнопка оплаты в боте */
export default function AgencyListingCard({ item, blocked }: AgencyListingCardProps) {
  const { lang, t } = useI18n();
  const at = t.agency;
  const { listing, active } = item;
  const image = listing.images?.[0];
  const status = active ? 'active' : 'off';
  const numbers: { icon: IconName; label: string; value: number }[] = [
    { icon: 'eye', label: at.stats.views, value: item.views },
    { icon: 'phone', label: at.stats.contacts, value: item.contacts },
    { icon: 'message', label: at.stats.chats, value: item.chats },
    { icon: 'calendar_check', label: at.stats.viewings, value: item.viewings },
    { icon: 'heart', label: at.stats.favorites, value: item.favorites },
  ];

  return (
    <article
      className="agency-listing flex min-w-0 flex-col gap-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[var(--shadow-sm)]"
      data-listing-id={listing.id}
    >
      <header className="flex min-w-0 gap-3">
        <div className="grid size-16 shrink-0 place-items-center overflow-hidden rounded-[var(--radius-md)] bg-[var(--surface-hover)] text-[var(--text-secondary)]">
          {image ? (
            <img
              src={image}
              alt=""
              loading="lazy"
              width={64}
              height={64}
              className="h-full w-full object-cover"
            />
          ) : (
            <Icon name="home" className="size-7 stroke-[1.5]" />
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-1">
          <h3 className="m-0 break-words text-sm font-semibold leading-5">
            {tr(listing.title, lang)}
          </h3>
          <ListingPrice
            listing={listing}
            monthly
            className="m-0 text-sm font-semibold"
            periodClassName="font-medium text-[var(--text-secondary)]"
          />
          <p className="m-0 flex flex-wrap gap-1.5">
            <span
              className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold leading-5 ${MY_CARD_STATUS_CLASS[status]}`}
            >
              {t.my_listings.status[status]}
            </span>
            {item.premium_until && (
              <span className="inline-flex items-center gap-1 rounded-full bg-[var(--promo-bg)] px-2 py-0.5 text-xs font-semibold leading-5 text-[var(--promo-text)]">
                <Icon name="star" className="size-3.5" />
                {fill(at.premium_until, formatDayMonth(item.premium_until, lang))}
              </span>
            )}
          </p>
        </div>
      </header>

      <dl className="agency-listing__numbers m-0 grid grid-cols-5 gap-1 rounded-[var(--radius-md)] bg-[var(--surface-hover)] p-2">
        {numbers.map(({ icon, label, value }) => (
          <div key={icon} className="flex min-w-0 flex-col items-center gap-0.5" title={label}>
            <dt className="text-[var(--text-secondary)]">
              <Icon name={icon} className="size-4" />
              <span className="sr-only">{label}</span>
            </dt>
            <dd className="m-0 text-sm font-semibold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>

      <footer className="flex flex-wrap gap-2">
        {active && !blocked && (
          <SignLink url={botSectionUrl('owner')} className={MY_CARD_ACTION_CLASS}>
            <Icon name="star" className="size-4" />
            {item.premium_until ? at.premium_extend : at.premium_make}
          </SignLink>
        )}
        {active && (
          <Link
            to={`/listing/${listing.id}`}
            className={MY_CARD_ACTION_CLASS}
            onClick={() => haptic('light')}
          >
            <Icon name="eye" className="size-4" />
            {t.my_listings.view}
          </Link>
        )}
      </footer>
    </article>
  );
}
