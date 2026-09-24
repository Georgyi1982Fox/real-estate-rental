import { Link } from 'react-router-dom';
import type { Listing } from '../api/types';
import type { DistrictNames } from '../hooks/useDistricts';
import { useFavorite } from '../hooks/useFavorite';
import { formatPrice, tr } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

interface ListingCardProps {
  listing: Listing;
  /** Резолвит listing.district (id) в читаемое имя; без словаря показывается сам id */
  districtNames?: DistrictNames;
  /** Уровень заголовка карточки в структуре страницы */
  headingLevel?: 'h2' | 'h3';
}

/**
 * Карточка объявления. Вся карточка кликабельна через «растянутую» ссылку заголовка;
 * кнопка избранного лежит над ней (z-10).
 */
export default function ListingCard({ listing, districtNames, headingLevel = 'h2' }: ListingCardProps) {
  const { lang, t } = useI18n();
  const { isFavorite, toggle } = useFavorite();
  const Heading = headingLevel;
  const title = tr(listing.title, lang);
  const districtEntry = districtNames?.[listing.district];
  const district = districtEntry ? tr(districtEntry, lang) : listing.district;
  const image = listing.images?.[0];

  return (
    <article
      className="listing-card group relative w-full max-w-full overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)] transition-all duration-200 focus-within:shadow-[var(--shadow-md)] hover:-translate-y-0.5 hover:shadow-[var(--shadow-md)]"
      data-listing-id={listing.id}
    >
      <figure className="listing-card__figure">
        <div className="listing-card__media relative aspect-[4/3] w-full overflow-hidden bg-[var(--surface-hover)]">
          {image ? (
            <img
              className="listing-card__image h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
              src={image}
              alt={title}
              loading="lazy"
              width={400}
              height={300}
            />
          ) : (
            <div
              className="listing-card__placeholder flex h-full w-full items-center justify-center text-sm text-[var(--text-secondary)]"
              role="img"
              aria-label={t.card.no_photo}
            >
              {t.card.no_photo}
            </div>
          )}

          <button
            type="button"
            className={`listing-card__favorite absolute right-3 top-3 z-10 inline-flex min-h-11 min-w-11 items-center justify-center rounded-full border border-white/60 bg-white/90 shadow-sm backdrop-blur-sm transition-colors duration-200 hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] focus-visible:ring-offset-2 ${isFavorite ? 'text-[var(--danger)]' : 'text-[var(--text-secondary)]'}`}
            aria-pressed={isFavorite}
            aria-label={t.card.favorite}
            onClick={toggle}
          >
            <span
              className={`text-xl leading-none transition-transform duration-200 ${isFavorite ? 'scale-110' : 'scale-100'}`}
              aria-hidden="true"
            >
              ♥
            </span>
          </button>
        </div>

        <figcaption className="listing-card__content space-y-3 p-4">
          <div className="listing-card__header min-w-0">
            <Heading className="listing-card__title break-words text-base font-semibold leading-6 text-[var(--text-primary)]">
              <Link
                to={`/listing/${listing.id}`}
                onClick={() => haptic('light')}
                className="listing-card__link after:absolute after:inset-0 after:rounded-[var(--radius-lg)] after:content-[''] focus-visible:outline-none focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-[var(--primary)]"
              >
                {title}
              </Link>
            </Heading>
            <p className="listing-card__price mt-1 text-lg font-bold leading-6 text-[var(--text-primary)]">
              {formatPrice(listing.price, listing.currency)}
            </p>
          </div>

          <p className="listing-card__district flex items-center gap-2 break-words text-sm text-[var(--text-secondary)]">
            <span aria-hidden="true">📍</span>
            <span>{district}</span>
          </p>

          <dl className="listing-card__meta grid grid-cols-2 gap-3 border-t border-[var(--border)] pt-3 text-sm text-[var(--text-secondary)]">
            <div className="listing-card__meta-item min-w-0">
              <dt className="sr-only">{t.card.rooms}</dt>
              <dd className="break-words">
                <span className="font-medium text-[var(--text-primary)]">{listing.rooms}</span>{' '}
                {t.card.rooms_unit}
              </dd>
            </div>
            <div className="listing-card__meta-item min-w-0 text-right">
              <dt className="sr-only">{t.card.area}</dt>
              <dd className="break-words">
                <span className="font-medium text-[var(--text-primary)]">{listing.area}</span>{' '}
                {t.card.sqm}
              </dd>
            </div>
          </dl>
        </figcaption>
      </figure>
    </article>
  );
}
