// Фильтры поиска: разбор адреса страницы, строка запроса для API, описание словами

import type { SearchFilters } from '../api/types';
import type { Strings } from '../i18n/strings';
import { fill, formatPrice } from './format';

export const PRICE_MAX = 10000;
export const PRICE_STEP = 100;
/** «4» в фильтре означает «4 и больше» */
export const ROOMS_MAX = 4;

export const FILTER_KEYS = ['district', 'min_price', 'max_price', 'rooms'] as const;

/** Целое число из адреса в диапазоне [min, max], иначе undefined */
function parseInteger(raw: string | null, min: number, max: number): number | undefined {
  if (raw === null || !/^\d+$/.test(raw)) return undefined;
  const value = Number(raw);
  return value >= min && value <= max ? value : undefined;
}

/** Фильтры из адреса страницы; мусорные значения отбрасываются */
export function parseFilters(params: URLSearchParams): SearchFilters {
  const filters: SearchFilters = {};
  const district = params.get('district')?.trim();
  if (district) filters.district = district;
  const minPrice = parseInteger(params.get('min_price'), 0, PRICE_MAX);
  if (minPrice !== undefined) filters.min_price = minPrice;
  const maxPrice = parseInteger(params.get('max_price'), 0, PRICE_MAX);
  if (maxPrice !== undefined) filters.max_price = maxPrice;
  const rooms = parseInteger(params.get('rooms'), 1, ROOMS_MAX);
  if (rooms !== undefined) filters.rooms = rooms;
  return filters;
}

/** Только заполненные фильтры, в постоянном порядке ключей */
function entries(filters: SearchFilters): [string, string][] {
  return FILTER_KEYS.flatMap((key) => {
    const value = filters[key];
    return value === undefined || value === '' ? [] : [[key, String(value)]];
  });
}

/** 'district=vake&rooms=2' — пустые значения не попадают в строку */
export function filtersToQuery(filters: SearchFilters): string {
  return new URLSearchParams(entries(filters)).toString();
}

export function hasFilters(filters: SearchFilters): boolean {
  return entries(filters).length > 0;
}

export function sameFilters(a: SearchFilters, b: SearchFilters): boolean {
  return filtersToQuery(a) === filtersToQuery(b);
}

/** «Ваке · 2 комн. · 800–2 000 ₾»; без фильтров — «Все квартиры» */
export function describeFilters(
  filters: SearchFilters,
  districtName: string,
  st: Strings['searches'],
): string {
  const parts: string[] = [];
  if (districtName) parts.push(districtName);
  if (filters.rooms !== undefined) {
    const rooms = filters.rooms >= ROOMS_MAX ? `${ROOMS_MAX}+` : String(filters.rooms);
    parts.push(fill(st.rooms, rooms));
  }
  const { min_price: min, max_price: max } = filters;
  if (min !== undefined && max !== undefined) {
    parts.push(`${formatPrice(min, '')}–${formatPrice(max)}`);
  } else if (min !== undefined) {
    parts.push(fill(st.price_from, formatPrice(min)));
  } else if (max !== undefined) {
    parts.push(fill(st.price_to, formatPrice(max)));
  }
  return parts.length > 0 ? parts.join(' · ') : st.all;
}
