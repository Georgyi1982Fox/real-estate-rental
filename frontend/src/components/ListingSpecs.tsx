import type { ReactNode } from 'react';
import type { Listing } from '../api/types';
import { formatPrice } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';

interface ListingSpecsProps {
  listing: Listing;
}

function SpecItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="listing-specs__item min-w-0 rounded-[var(--radius-md)] bg-[var(--surface-hover)] p-3">
      <dt className="text-xs text-[var(--text-secondary)]">{label}</dt>
      <dd className="mt-1 text-base font-semibold">{children}</dd>
    </div>
  );
}

/** Характеристики + удобства. Необязательные поля показываются, только если пришли числом */
export default function ListingSpecs({ listing }: ListingSpecsProps) {
  const { t } = useI18n();
  const lt = t.listing;
  const featureNames: Record<string, string> = lt.features;
  const features = listing.features ?? [];

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
        {typeof listing.bedrooms === 'number' && <SpecItem label={lt.bedrooms}>{listing.bedrooms}</SpecItem>}
        <SpecItem label={lt.area}>
          {listing.area} {t.card.sqm}
        </SpecItem>
        {typeof listing.floor === 'number' && (
          <SpecItem label={lt.floor}>
            {listing.floor}
            {typeof listing.total_floors === 'number' && ` / ${listing.total_floors}`}
          </SpecItem>
        )}
        {typeof listing.deposit === 'number' && (
          <SpecItem label={lt.deposit}>{formatPrice(listing.deposit, listing.currency)}</SpecItem>
        )}
      </dl>

      {features.length > 0 && (
        <>
          <h3 className="pt-2 text-sm font-semibold text-[var(--text-secondary)]">{lt.amenities}</h3>
          <ul className="listing-specs__features flex list-none flex-wrap gap-2 p-0">
            {features.map((code) => (
              <li
                key={code}
                className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] px-3 py-1.5 text-sm"
              >
                <span className="text-[var(--secondary)]" aria-hidden="true">
                  ✓
                </span>
                {featureNames[code] ?? code}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
