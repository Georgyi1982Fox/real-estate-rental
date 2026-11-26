import type { Listing } from '../api/types';

/**
 * Квартиры на карте поиска (FRONTEND-056): квартиры одного дома — одна точка.
 * Сколько ни увеличивай карту, квартиры одного дома не разойдутся, поэтому точки ближе
 * этого расстояния считаются одним домом. Разные дома рядом расходятся при увеличении сами.
 */
export const SAME_BUILDING_M = 25;

/** Метров в одном градусе широты (и долготы на экваторе) */
const METERS_PER_DEGREE = 111_320;

export type MappedListing = Listing & { latitude: number; longitude: number };

export interface MapGroup {
  /** id первой квартиры: не меняется, пока дом на карте */
  key: string;
  latitude: number;
  longitude: number;
  listings: MappedListing[];
}

/** Есть ли у квартиры настоящая точка */
export function hasPoint(listing: Listing): listing is MappedListing {
  return (
    typeof listing.latitude === 'number' &&
    typeof listing.longitude === 'number' &&
    Number.isFinite(listing.latitude) &&
    Number.isFinite(listing.longitude)
  );
}

/** Расстояние в метрах; на расстояниях в десятки метров плоская формула точна */
function distanceM(a: { latitude: number; longitude: number }, b: MappedListing): number {
  const dy = (b.latitude - a.latitude) * METERS_PER_DEGREE;
  const dx =
    (b.longitude - a.longitude) * METERS_PER_DEGREE * Math.cos((a.latitude * Math.PI) / 180);
  return Math.hypot(dx, dy);
}

/**
 * Квартиры страницы → дома на карте, в порядке результатов поиска.
 * missing — сколько квартир без точки (их видно только в списке)
 */
export function groupByBuilding(listings: Listing[]): { groups: MapGroup[]; missing: number } {
  const groups: MapGroup[] = [];
  let missing = 0;
  for (const listing of listings) {
    if (!hasPoint(listing)) {
      missing += 1;
      continue;
    }
    const home = groups.find((group) => distanceM(group, listing) < SAME_BUILDING_M);
    if (home) home.listings.push(listing);
    else {
      groups.push({
        key: String(listing.id),
        latitude: listing.latitude,
        longitude: listing.longitude,
        listings: [listing],
      });
    }
  }
  return { groups, missing };
}
