import { Link } from 'react-router-dom';
import type { MyHotel, MyHotelStatus } from '../api/types';
import type { CityNames } from '../hooks/useCity';
import { hotelKindName } from '../i18n/hotels';
import { isPromotedNow } from '../hooks/useHotelPromotion';
import { fillVars, formatDayMonth, plural, tr } from '../lib/format';
import { HOTELS_PATH, MY_HOTELS_PATH } from '../lib/hotels';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import HotelPrice from './HotelPrice';
import Icon from './Icon';

export const MY_CARD_ACTION_CLASS =
  'inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-hover)] active:scale-[.98] disabled:opacity-60';

const TOP_CLASS =
  'my-hotel-card__top inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-4 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98] disabled:opacity-70';

export const MY_CARD_STATUS_CLASS: Record<MyHotelStatus, string> = {
  active: 'bg-[var(--success-bg)] text-[var(--success-text)]',
  off: 'bg-[var(--surface-hover)] text-[var(--text-secondary)]',
  hidden: 'bg-[var(--danger-bg)] text-[var(--danger-text)]',
};

interface MyHotelCardProps {
  hotel: MyHotel;
  cityNames: CityNames;
  busy: boolean;
  /** Снять с показа (false) или вернуть (true) */
  onToggle: (active: boolean) => void;
  onDelete: () => void;
  /** «🔥 Топ» из GET /api/hotels/options; нет — кнопку не показываем */
  promotion?: { price: number; days: number };
  /** Идёт оплата «Топ» этого объекта */
  paying: boolean;
  onPromote: () => void;
}

/** Свой объект в «Моих гостиницах»: статус и действия — изменить, снять / вернуть, удалить */
export default function MyHotelCard({
  hotel,
  cityNames,
  busy,
  onToggle,
  onDelete,
  promotion,
  paying,
  onPromote,
}: MyHotelCardProps) {
  const { lang, t } = useI18n();
  const mt = t.my_hotels;
  const name = tr(hotel.name, lang);
  const image = hotel.images?.[0];
  const kind = hotelKindName(hotel.kind, lang);
  const cityEntry = cityNames[hotel.city];
  const city = cityEntry ? tr(cityEntry, lang) : hotel.city;
  const status: MyHotelStatus = hotel.status in MY_CARD_STATUS_CLASS ? hotel.status : 'off';
  const noRooms = (hotel.rooms ?? []).length === 0;
  const promoted = isPromotedNow(hotel);
  // «Топ» — только у объекта в разделе: включён и есть номер с ценой
  const canPromote = status === 'active' && typeof hotel.min_price === 'number';
  const topText = !promotion
    ? ''
    : paying
      ? mt.top_paying
      : promoted
        ? fillVars(mt.top_renew, { price: promotion.price })
        : fillVars(mt.top_buy, {
            days: plural(t.premium.days, promotion.days, lang),
            price: promotion.price,
          });

  return (
    <article
      className="my-hotel-card flex min-w-0 flex-col gap-4 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[var(--shadow-sm)]"
      data-hotel-id={hotel.id}
    >
      <header className="flex min-w-0 gap-3">
        <div className="my-hotel-card__media grid size-20 shrink-0 place-items-center overflow-hidden rounded-[var(--radius-md)] bg-[var(--surface-hover)] text-[var(--text-secondary)]">
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
            <Icon name="hotel" className="size-8 stroke-[1.5]" />
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-1">
          <p
            className={`my-hotel-card__status m-0 inline-flex rounded-full px-2 py-0.5 text-xs font-semibold leading-5 ${MY_CARD_STATUS_CLASS[status]}`}
          >
            {mt.status[status]}
          </p>
          <h2 className="m-0 break-words text-base font-semibold leading-6">{name}</h2>
          <p className="m-0 text-xs text-[var(--text-secondary)]">
            {[kind, city].filter(Boolean).join(' · ')}
          </p>
          <HotelPrice
            price={hotel.min_price}
            className="m-0 text-sm font-semibold"
            periodClassName="font-medium text-[var(--text-secondary)]"
          />
        </div>
      </header>

      {promoted && hotel.promoted_until && (
        <p className="my-hotel-card__promoted m-0 rounded-[var(--radius-md)] bg-[var(--success-bg)] px-3 py-2 text-xs font-semibold text-[var(--success-text)]">
          {fillVars(mt.top_until, { date: formatDayMonth(hotel.promoted_until, lang) })}
        </p>
      )}

      {noRooms && (
        <p className="m-0 rounded-[var(--radius-md)] bg-[var(--warning-bg)] px-3 py-2 text-xs font-medium text-[var(--warning-text)]">
          {mt.no_rooms}
        </p>
      )}

      {canPromote && promotion && (
        <button
          type="button"
          className={TOP_CLASS}
          disabled={paying}
          aria-busy={paying}
          onClick={() => {
            haptic('light');
            onPromote();
          }}
        >
          {paying && <span className="spinner" aria-hidden="true" />}
          {topText}
        </button>
      )}

      <footer className="my-hotel-card__actions flex flex-wrap gap-2">
        <Link
          to={`${MY_HOTELS_PATH}/${hotel.id}/edit`}
          className={MY_CARD_ACTION_CLASS}
          onClick={() => haptic('light')}
        >
          <Icon name="pencil" className="size-4" />
          {mt.edit}
        </Link>
        {/* Скрытый модерацией объект хозяин вернуть не может */}
        {status !== 'hidden' && (
          <button
            type="button"
            className={MY_CARD_ACTION_CLASS}
            disabled={busy}
            onClick={() => {
              haptic('light');
              onToggle(status !== 'active');
            }}
          >
            {status === 'active' ? mt.take_down : mt.put_back}
          </button>
        )}
        {status === 'active' && (
          <Link
            to={`${HOTELS_PATH}/${hotel.id}`}
            className={MY_CARD_ACTION_CLASS}
            onClick={() => haptic('light')}
          >
            <Icon name="eye" className="size-4" />
            {mt.view}
          </Link>
        )}
        <button
          type="button"
          className={`${MY_CARD_ACTION_CLASS} text-[var(--danger)]`}
          disabled={busy}
          aria-haspopup="dialog"
          onClick={() => {
            haptic('light');
            onDelete();
          }}
        >
          <Icon name="trash" className="size-4" />
          {mt.delete}
        </button>
      </footer>
    </article>
  );
}
