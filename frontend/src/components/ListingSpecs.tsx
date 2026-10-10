import type { Listing } from '../api/types';
import { conditionName } from '../i18n/conditions';
import { fillVars, formatPrice } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import ListingAmenities from './ListingAmenities';
import SpecItem from './SpecItem';

interface ListingSpecsProps {
  listing: Listing;
}

/**
 * Характеристики + удобства. Необязательные поля показываются, только если сайт их указал:
 * null, отсутствующее поле и неизвестный код — строки нет.
 */
export default function ListingSpecs({ listing }: ListingSpecsProps) {
  const { lang, t } = useI18n();
  const lt = t.listing;
  const condition = conditionName(listing.condition, lang);
  const ownerType =
    listing.owner_type === 'owner' || listing.owner_type === 'agent'
      ? lt.owner_types[listing.owner_type]
      : '';

  return (
    <section
      className="listing-specs space-y-4 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5"
      aria-labelledby="listing-specs-title"
    >
      <h2 id="listing-specs-title" className="text-lg font-semibold">
        {lt.specs}
      </h2>
      <dl className="listing-specs__grid grid grid-cols-2 gap-3 sm:grid-cols-3">
        <SpecItem label={lt.rooms}>{listing.rooms}</SpecItem>
        {typeof listing.bedrooms === 'number' && (
          <SpecItem label={lt.bedrooms}>{listing.bedrooms}</SpecItem>
        )}
        {typeof listing.bathrooms === 'number' && (
          <SpecItem label={lt.bathrooms}>{listing.bathrooms}</SpecItem>
        )}
        <SpecItem label={lt.area}>
          {listing.area} {t.card.sqm}
        </SpecItem>
        {typeof listing.floor === 'number' && (
          <SpecItem label={lt.floor}>
            {typeof listing.total_floors === 'number'
              ? fillVars(lt.floor_of, { floor: listing.floor, total: listing.total_floors })
              : listing.floor}
          </SpecItem>
        )}
        {condition && <SpecItem label={lt.condition}>{condition}</SpecItem>}
        {typeof listing.deposit === 'number' && (
          <SpecItem label={lt.deposit}>{formatPrice(listing.deposit, listing.currency)}</SpecItem>
        )}
        {ownerType && <SpecItem label={lt.listed_by}>{ownerType}</SpecItem>}
      </dl>

      <ListingAmenities codes={listing.features ?? []} />
    </section>
  );
}
