import { Link } from 'react-router-dom';
import type { MyHotelStatus, MyListing } from '../api/types';
import { botSectionUrl } from '../lib/config';
import { tr } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import ListingPrice from './ListingPrice';
import { MY_CARD_ACTION_CLASS, MY_CARD_STATUS_CLASS } from './MyHotelCard';
import PromotionBadges from './PromotionBadges';
import SignLink from './SignLink';

interface MyListingCardProps {
  listing: MyListing;
  busy: boolean;
  /** Снять с поиска (false) или вернуть (true) */
  onToggle: (active: boolean) => void;
  onPrice: () => void;
  onPhotos: () => void;
}

/** Своё объявление: статус, значки и действия — снять / вернуть, цена, фото, топ и проверка */
export default function MyListingCard({
  listing,
  busy,
  onToggle,
  onPrice,
  onPhotos,
}: MyListingCardProps) {
  const { lang, t } = useI18n();
  const mt = t.my_listings;
  const image = listing.images?.[0];
  const status: MyHotelStatus = listing.status in MY_CARD_STATUS_CLASS ? listing.status : 'off';
  const active = status === 'active';

  return (
    <article
      className="my-listing-card flex min-w-0 flex-col gap-4 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[var(--shadow-sm)]"
      data-listing-id={listing.id}
    >
      <header className="flex min-w-0 gap-3">
        <div className="my-listing-card__media grid size-20 shrink-0 place-items-center overflow-hidden rounded-[var(--radius-md)] bg-[var(--surface-hover)] text-[var(--text-secondary)]">
          {image ? (
            <img
              src={image}
              alt=""
              loading="lazy"
              width={80}
              height={80}
              className="h-full w-full object-cover"
            />
          ) : (
            <Icon name="home" className="size-8 stroke-[1.5]" />
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-1">
          <p
            className={`my-listing-card__status m-0 inline-flex rounded-full px-2 py-0.5 text-xs font-semibold leading-5 ${MY_CARD_STATUS_CLASS[status]}`}
          >
            {mt.status[status]}
          </p>
          <h2 className="m-0 break-words text-base font-semibold leading-6">
            {tr(listing.title, lang)}
          </h2>
          <ListingPrice
            listing={listing}
            monthly
            className="m-0 text-sm font-semibold"
            periodClassName="font-medium text-[var(--text-secondary)]"
          />
          <PromotionBadges
            promoted={listing.is_promoted === true}
            verified={listing.is_verified === true}
          />
        </div>
      </header>

      <footer className="my-listing-card__actions flex flex-wrap gap-2">
        {/* Скрытое модератором объявление хозяин вернуть не может */}
        {status !== 'hidden' && (
          <button
            type="button"
            className={MY_CARD_ACTION_CLASS}
            disabled={busy}
            onClick={() => {
              haptic('light');
              onToggle(!active);
            }}
          >
            {active ? mt.take_down : mt.put_back}
          </button>
        )}
        <button
          type="button"
          className={MY_CARD_ACTION_CLASS}
          disabled={busy}
          aria-haspopup="dialog"
          onClick={() => {
            haptic('light');
            onPrice();
          }}
        >
          {mt.change_price}
        </button>
        <button
          type="button"
          className={MY_CARD_ACTION_CLASS}
          aria-haspopup="dialog"
          onClick={() => {
            haptic('light');
            onPhotos();
          }}
        >
          <Icon name="image" className="size-4" />
          {mt.photos} {listing.images?.length ?? 0}
        </button>
        {active && (
          <Link
            to={`/listing/${listing.id}`}
            className={MY_CARD_ACTION_CLASS}
            onClick={() => haptic('light')}
          >
            <Icon name="eye" className="size-4" />
            {mt.view}
          </Link>
        )}
      </footer>

      {/* Оплата топа и документ о собственности — в боте */}
      {active && (
        <section className="my-listing-card__bot flex flex-col gap-2 border-t border-[var(--border)] pt-3">
          <div className="flex flex-wrap gap-2">
            <SignLink url={botSectionUrl('owner')} className={MY_CARD_ACTION_CLASS}>
              {mt.top}
            </SignLink>
            {listing.is_verified !== true && (
              <SignLink url={botSectionUrl('owner')} className={MY_CARD_ACTION_CLASS}>
                {mt.verify}
              </SignLink>
            )}
          </div>
          <p className="m-0 text-xs text-[var(--text-secondary)]">{mt.bot_hint}</p>
        </section>
      )}
    </article>
  );
}
