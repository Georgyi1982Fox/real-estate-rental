// Фильтры поиска гостиниц: разбор адреса страницы, строка запроса для GET /api/hotels, чипы

import type { HotelFilters } from '../api/types';
import { hotelAmenityName, hotelKindName } from '../i18n/hotels';
import type { Lang, Strings } from '../i18n/strings';
import { fill } from './format';
import { priceLabel } from './searchFilters';

/** Цена ночи, которую принимает бэкенд: от 10 до 5 000 ₾ */
export const HOTEL_PRICE_MAX = 5000;
export const HOTEL_PRICE_STEP = 10;
export const HOTEL_STARS_MAX = 5;
/** Последняя таблетка «Гостей» — «6+»: на сервер уходит 6 */
export const HOTEL_GUESTS_MAX = 6;
/** Столько кодов типа или удобств берём из адреса */
const CODES_MAX = 30;

/** Параметры адреса страницы и запроса — одни и те же; списки через запятую: kind=hotel,hostel */
export const HOTEL_FILTER_KEYS = [
  'kind',
  'guests',
  'price_min',
  'price_max',
  'stars',
  'amenities',
] as const;

export const HOTEL_SORT_KEY = 'sort';
/** Что умеет GET /api/hotels?sort=; без параметра сервер отдаёт newest */
export const HOTEL_SORTS = ['newest', 'price_asc', 'price_desc', 'stars_desc'] as const;
export type HotelSort = (typeof HOTEL_SORTS)[number];
export const HOTEL_DEFAULT_SORT: HotelSort = 'newest';

const NUMBER_LIMITS = {
  guests: [1, HOTEL_GUESTS_MAX],
  price_min: [0, HOTEL_PRICE_MAX],
  price_max: [0, HOTEL_PRICE_MAX],
  stars: [1, HOTEL_STARS_MAX],
} as const;
const NUMBER_KEYS = Object.keys(NUMBER_LIMITS) as (keyof typeof NUMBER_LIMITS)[];
const LIST_KEYS = ['kind', 'amenities'] as const;

/** Сортировка из адреса; незнакомое значение — как будто её нет */
export function parseHotelSort(raw: string | null): HotelSort | undefined {
  return HOTEL_SORTS.find((order) => order === raw);
}

function parseInteger(raw: string | null, min: number, max: number): number | undefined {
  if (raw === null || !/^\d+$/.test(raw)) return undefined;
  const value = Number(raw);
  return value >= min && value <= max ? value : undefined;
}

/** Уникальные непустые коды в исходном порядке: и ?key=a,b, и ?key=a&key=b */
function listParam(params: URLSearchParams, key: string): string[] {
  const codes = params
    .getAll(key)
    .flatMap((value) => value.split(','))
    .map((code) => code.trim())
    .filter(Boolean);
  return [...new Set(codes)].slice(0, CODES_MAX);
}

/** Фильтры из адреса страницы; мусорные значения отбрасываются */
export function parseHotelFilters(params: URLSearchParams): HotelFilters {
  const filters: HotelFilters = {};
  NUMBER_KEYS.forEach((key) => {
    const [min, max] = NUMBER_LIMITS[key];
    const value = parseInteger(params.get(key), min, max);
    if (value !== undefined) filters[key] = value;
  });
  LIST_KEYS.forEach((key) => {
    const codes = listParam(params, key);
    if (codes.length > 0) filters[key] = codes;
  });
  return filters;
}

/** Только заполненные фильтры, в постоянном порядке ключей; списки отсортированы */
export function hotelFilterEntries(filters: HotelFilters): [string, string][] {
  const entries: [string, string][] = [];
  const kinds = [...(filters.kind ?? [])].sort();
  if (kinds.length > 0) entries.push(['kind', kinds.join(',')]);
  NUMBER_KEYS.forEach((key) => {
    const value = filters[key];
    if (value != null) entries.push([key, String(value)]);
  });
  const amenities = [...(filters.amenities ?? [])].sort();
  if (amenities.length > 0) entries.push(['amenities', amenities.join(',')]);
  return entries;
}

/**
 * Строка запроса для /api/hotels: город (общий для приложения, см. useCity) + фильтры +
 * сортировка. Без city сервер ищет по всей стране
 */
export function hotelsQuery(
  filters: HotelFilters,
  city: string | undefined,
  sort?: HotelSort,
): string {
  const params = new URLSearchParams(hotelFilterEntries(filters));
  if (city) params.set('city', city);
  if (sort) params.set(HOTEL_SORT_KEY, sort);
  // Запятую не кодируем: бэкенд понимает оба варианта, а адрес читается глазами
  return params.toString().replace(/%2C/gi, ',');
}

export function hasHotelFilters(filters: HotelFilters): boolean {
  return hotelFilterEntries(filters).length > 0;
}

/** Сколько фильтров выбрано: границы цены — один фильтр, списки — по одному на список */
export function countHotelFilters(filters: HotelFilters): number {
  const keys = hotelFilterEntries(filters).map(([key]) => (key === 'price_max' ? 'price_min' : key));
  return new Set(keys).size;
}

/** Чип выбранного фильтра; patch убирает этот фильтр (нужные поля — undefined) */
export interface HotelFilterChip {
  key: string;
  label: string;
  patch: HotelFilters;
}

/** Фильтр звёзд — «не меньше N»: «от 3 ★», у пяти — просто «5 ★» */
export function starsText(value: number, st: Strings['searches']): string {
  const stars = `${value} ★`;
  return value >= HOTEL_STARS_MAX ? stars : fill(st.price_from, stars);
}

/** «3» или «6+» в фильтре гостей */
export function guestsText(value: number): string {
  return value >= HOTEL_GUESTS_MAX ? `${HOTEL_GUESTS_MAX}+` : String(value);
}

/**
 * Чипы под строкой фильтров: тип и удобство — по чипу на код (убираются по одному),
 * гости, цена, звёзды. Неизвестный код показывается как есть
 */
export function hotelFilterChips(filters: HotelFilters, t: Strings, lang: Lang): HotelFilterChip[] {
  const ht = t.hotels;
  const chips: HotelFilterChip[] = [];
  const without = (codes: string[], code: string) => {
    const rest = codes.filter((item) => item !== code);
    return rest.length > 0 ? rest : undefined;
  };
  const kinds = filters.kind ?? [];
  kinds.forEach((code) => {
    chips.push({
      key: `kind:${code}`,
      label: hotelKindName(code, lang) ?? code,
      patch: { kind: without(kinds, code) },
    });
  });
  if (filters.guests != null) {
    chips.push({
      key: 'guests',
      label: fill(ht.guests_chip, guestsText(filters.guests)),
      patch: { guests: undefined },
    });
  }
  const price = priceLabel({ min: filters.price_min, max: filters.price_max }, t.searches);
  if (price) {
    chips.push({
      key: 'price',
      label: price,
      patch: { price_min: undefined, price_max: undefined },
    });
  }
  if (filters.stars != null) {
    chips.push({
      key: 'stars',
      label: starsText(filters.stars, t.searches),
      patch: { stars: undefined },
    });
  }
  const amenities = filters.amenities ?? [];
  amenities.forEach((code) => {
    chips.push({
      key: `amenities:${code}`,
      label: hotelAmenityName(code, lang) ?? code,
      patch: { amenities: without(amenities, code) },
    });
  });
  return chips;
}
