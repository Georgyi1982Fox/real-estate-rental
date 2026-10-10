import { Link } from 'react-router-dom';
import type { HotelSummary } from '../api/types';
import type { CityNames } from '../hooks/useCity';
import { hotelKindName } from '../i18n/hotels';
import { fill, tr } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import CardGallery from './CardGallery';
import HotelPrice from './HotelPrice';
import Icon from './Icon';
import PromotionBadges from './PromotionBadges';
import RatingStars from './RatingStars';

interface HotelCardProps {
  hotel: HotelSummary;
  /** Резолвит hotel.city (код) в название; без словаря показывается сам код */
  cityNames?: CityNames;
  /** Уровень заголовка карточки в структуре страницы */
  headingLevel?: 'h2' | 'h3';
}

/**
 * Карточка гостиницы: фото, название, тип, звёзды, «от N ₾ / ночь», значки «Топ» и «Проверено».
 * Вся карточка кликабельна через «растянутую» ссылку заголовка; «Топ» — с оранжевой рамкой
 */
export default function HotelCard({ hotel, cityNames, headingLevel = 'h2' }: HotelCardProps) {
  const { lang, t } = useI18n();
  const ht = t.hotels;
  const Heading = headingLevel;
  const name = tr(hotel.name, lang);
  const to = `/hotels/${hotel.id}`;
  const images = hotel.images ?? [];
  const image = images[0];
  const kind = hotelKindName(hotel.kind, lang);
  const cityEntry = cityNames?.[hotel.city];
  const city = cityEntry ? tr(cityEntry, lang) : hotel.city;
  const place = [city, hotel.address].filter(Boolean).join(', ');

  return (
    <article
      className={`hotel-card group relative w-full max-w-full overflow-hidden rounded-[var(--radius-lg)] border bg-[var(--surface)] shadow-[var(--shadow-sm)] transition-all duration-200 focus-within:shadow-[var(--shadow-md)] hover:-translate-y-0.5 hover:shadow-[var(--shadow-md)] ${
        hotel.is_promoted ? 'hotel-card--promoted border-[var(--promo-border)]' : 'border-[var(--border)]'
      }`}
      data-hotel-id={hotel.id}
    >
      <figure className="hotel-card__figure">
        <div className="hotel-card__media relative aspect-[4/3] w-full overflow-hidden bg-[var(--surface-hover)]">
          {images.length > 1 ? (
            <CardGallery images={images} alt={name} to={to} />
          ) : image ? (
            <img
              className="hotel-card__image h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
              src={image}
              alt={name}
              loading="lazy"
              width={400}
              height={300}
            />
          ) : (
            <div
              className="hotel-card__placeholder flex h-full w-full items-center justify-center text-sm text-[var(--text-secondary)]"
              role="img"
              aria-label={t.card.no_photo}
            >
              {t.card.no_photo}
            </div>
          )}
          <PromotionBadges
            promoted={hotel.is_promoted}
            verified={hotel.is_verified}
            className="hotel-card__badges pointer-events-none absolute left-3 top-3 z-10 max-w-[calc(100%-1.5rem)]"
          />
        </div>

        <figcaption className="hotel-card__content space-y-3 p-4">
          <div className="hotel-card__header min-w-0">
            {(kind || typeof hotel.stars === 'number') && (
              <p className="hotel-card__kind m-0 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs font-medium text-[var(--text-secondary)]">
                {kind && <span>{kind}</span>}
                {typeof hotel.stars === 'number' && <RatingStars value={hotel.stars} />}
              </p>
            )}
            <Heading className="hotel-card__title mt-1 break-words text-base font-semibold leading-6 text-[var(--text-primary)]">
              <Link
                to={to}
                onClick={() => haptic('light')}
                className="hotel-card__link after:absolute after:inset-0 after:rounded-[var(--radius-lg)] after:content-[''] focus-visible:outline-none focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-[var(--primary)]"
              >
                {name}
              </Link>
            </Heading>
            <HotelPrice
              price={hotel.min_price}
              className="hotel-card__price m-0 mt-1 text-lg font-bold leading-6 text-[var(--text-primary)]"
              periodClassName="text-sm font-medium text-[var(--text-secondary)]"
            />
          </div>

          <ul className="hotel-card__meta m-0 flex list-none flex-col gap-1.5 border-t border-[var(--border)] p-0 pt-3 text-sm text-[var(--text-secondary)]">
            {place && (
              <li className="flex min-w-0 items-start gap-2">
                <Icon name="pin" className="mt-0.5 size-4" />
                <span className="min-w-0 break-words">{place}</span>
              </li>
            )}
            {typeof hotel.max_guests === 'number' && (
              <li className="flex min-w-0 items-center gap-2">
                <Icon name="users" className="size-4" />
                <span>{fill(ht.max_guests, hotel.max_guests)}</span>
              </li>
            )}
          </ul>
        </figcaption>
      </figure>
    </article>
  );
}
