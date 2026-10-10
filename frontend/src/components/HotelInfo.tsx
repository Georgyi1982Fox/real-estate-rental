import type { Hotel } from '../api/types';
import { hotelAmenityName, hotelKindName } from '../i18n/hotels';
import { fill } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import AmenityGrid from './AmenityGrid';
import type { IconName } from './Icon';
import SpecItem from './SpecItem';

interface HotelInfoProps {
  hotel: Hotel;
}

const AMENITY_ICONS: Record<string, IconName> = {
  wifi: 'wifi',
  parking: 'parking',
  breakfast: 'coffee',
  air_conditioning: 'snowflake',
  kitchen: 'pot',
  pool: 'waves',
  restaurant: 'utensils',
  spa: 'droplet',
  gym: 'dumbbell',
  airport_transfer: 'car',
  reception_24h: 'clock',
  pets_allowed: 'paw',
  family_rooms: 'users',
  sea_view: 'waves',
  mountain_view: 'mountain',
  elevator: 'elevator',
};

/**
 * Характеристики гостиницы: тип, гости, заезд и выезд, удобства значками.
 * Незаданное поле и неизвестный код — строки нет
 */
export default function HotelInfo({ hotel }: HotelInfoProps) {
  const { lang, t } = useI18n();
  const ht = t.hotels;
  const kind = hotelKindName(hotel.kind, lang);
  // Набор убирает повторы кодов
  const amenities = [...new Set(hotel.amenities ?? [])].flatMap((code) => {
    const name = hotelAmenityName(code, lang);
    const icon: IconName = AMENITY_ICONS[code] ?? 'check';
    return name ? [{ code, name, icon }] : [];
  });

  return (
    <section
      className="listing-specs space-y-4 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5"
      aria-labelledby="hotel-info-title"
    >
      <h2 id="hotel-info-title" className="text-lg font-semibold">
        {t.listing.specs}
      </h2>
      <dl className="listing-specs__grid grid grid-cols-2 gap-3 sm:grid-cols-3">
        {kind && <SpecItem label={ht.kind}>{kind}</SpecItem>}
        {typeof hotel.max_guests === 'number' && (
          <SpecItem label={ht.guests}>{fill(ht.max_guests, hotel.max_guests)}</SpecItem>
        )}
        {hotel.check_in && (
          <SpecItem label={ht.check_in}>{fill(ht.time_from, hotel.check_in)}</SpecItem>
        )}
        {hotel.check_out && (
          <SpecItem label={ht.check_out}>{fill(ht.time_until, hotel.check_out)}</SpecItem>
        )}
      </dl>

      <AmenityGrid title={ht.amenities} items={amenities} />
    </section>
  );
}
