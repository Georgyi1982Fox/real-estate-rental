import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import type { DistrictNames } from '../hooks/useDistricts';
import { plural, tr } from '../lib/format';
import { rememberListingPreview } from '../lib/listingPreview';
import type { MapGroup, MappedListing } from '../lib/mapGroups';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import ListingPrice from './ListingPrice';

// На телефоне листают пальцем — стрелки только с мышью (и они не теснят заголовок)
const ARROW_CLASS =
  'map-sheet__arrow pointer-coarse:hidden inline-flex size-9 shrink-0 items-center justify-center rounded-full text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] disabled:opacity-30 disabled:hover:bg-transparent active:scale-[.95]';

interface MapListingSheetProps {
  group: MapGroup;
  districtNames: DistrictNames;
  onClose: () => void;
}

/**
 * Карточка внизу карты поиска (FRONTEND-056): нажали точку — квартира, нажали дом с
 * несколькими квартирами — они листаются пальцем вбок (или стрелками), «1 / 3».
 * Нажали на квартиру — её страница.
 */
export default function MapListingSheet({ group, districtNames, onClose }: MapListingSheetProps) {
  const { lang, t } = useI18n();
  const mt = t.home.map;
  const trackRef = useRef<HTMLUListElement>(null);
  const [index, setIndex] = useState(0);
  const count = group.listings.length;
  const many = count > 1;
  const first = group.listings[0];

  // С карточки страница квартиры открывается сразу, как из списка
  useEffect(() => group.listings.forEach(rememberListingPreview), [group]);

  const scrollTo = (next: number) => {
    const track = trackRef.current;
    if (!track) return;
    haptic('selection');
    track.scrollTo({ left: next * track.clientWidth, behavior: 'smooth' });
  };

  return (
    <div
      className="map-sheet rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-md)]"
      role="dialog"
      aria-label={many ? plural(mt.building, count, lang) : first ? tr(first.title, lang) : ''}
    >
      <div className="map-sheet__header flex min-h-11 items-center gap-1 py-1 pl-4 pr-1">
        <p className="m-0 min-w-0 flex-1 truncate text-sm font-semibold text-[var(--text-primary)]">
          {many && plural(mt.building, count, lang)}
        </p>
        {many && (
          <>
            <button
              type="button"
              className={ARROW_CLASS}
              aria-label={mt.prev}
              disabled={index === 0}
              onClick={() => scrollTo(index - 1)}
            >
              <Icon name="chevron" className="size-4 rotate-180" />
            </button>
            <span
              className="map-sheet__counter min-w-10 text-center text-xs font-medium tabular-nums text-[var(--text-secondary)]"
              aria-live="polite"
            >
              {index + 1} / {count}
            </span>
            <button
              type="button"
              className={ARROW_CLASS}
              aria-label={mt.next}
              disabled={index === count - 1}
              onClick={() => scrollTo(index + 1)}
            >
              <Icon name="chevron" className="size-4" />
            </button>
          </>
        )}
        <button
          type="button"
          className="map-sheet__close inline-flex size-11 shrink-0 items-center justify-center rounded-full text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] active:scale-[.95]"
          aria-label={t.common.close}
          onClick={onClose}
        >
          <Icon name="close" className="size-5" />
        </button>
      </div>
      <ul
        ref={trackRef}
        className="map-sheet__track m-0 flex snap-x snap-mandatory list-none overflow-x-auto overscroll-x-contain p-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        onScroll={(event) => {
          const track = event.currentTarget;
          setIndex(Math.round(track.scrollLeft / Math.max(1, track.clientWidth)));
        }}
      >
        {group.listings.map((listing) => (
          <li key={listing.id} className="w-full shrink-0 snap-center px-3 pb-3">
            <SheetListing listing={listing} districtNames={districtNames} />
          </li>
        ))}
      </ul>
    </div>
  );
}

function SheetListing({
  listing,
  districtNames,
}: {
  listing: MappedListing;
  districtNames: DistrictNames;
}) {
  const { lang, t } = useI18n();
  const title = tr(listing.title, lang);
  const districtEntry = districtNames[listing.district];
  const district = districtEntry ? tr(districtEntry, lang) : listing.district;
  const image = listing.images?.[0];

  return (
    <Link
      to={`/listing/${listing.id}`}
      onClick={() => haptic('light')}
      className="map-sheet__listing flex min-w-0 gap-3 rounded-[var(--radius-md)] text-left hover:bg-[var(--surface-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)]"
    >
      <div className="map-sheet__media relative size-24 shrink-0 overflow-hidden rounded-[var(--radius-md)] bg-[var(--surface-hover)]">
        {image ? (
          <img src={image} alt="" className="h-full w-full object-cover" width={96} height={96} />
        ) : (
          <span className="flex h-full w-full items-center justify-center p-1 text-center text-xs text-[var(--text-secondary)]">
            {t.card.no_photo}
          </span>
        )}
      </div>
      <div className="map-sheet__info flex min-w-0 flex-1 flex-col justify-center gap-1 py-1 pr-1">
        <span className="sr-only">{title}</span>
        <ListingPrice
          listing={listing}
          className="m-0 text-base font-bold leading-6 text-[var(--text-primary)]"
          periodClassName="text-xs font-medium text-[var(--text-secondary)]"
        />
        <span className="text-sm text-[var(--text-secondary)]">
          <span className="font-medium text-[var(--text-primary)]">{listing.rooms}</span>{' '}
          {t.card.rooms_unit} ·{' '}
          <span className="font-medium text-[var(--text-primary)]">{listing.area}</span>{' '}
          {t.card.sqm}
        </span>
        {district && (
          <span className="flex min-w-0 items-center gap-1.5 text-sm text-[var(--text-secondary)]">
            <span aria-hidden="true">📍</span>
            <span className="truncate">{district}</span>
          </span>
        )}
      </div>
    </Link>
  );
}
