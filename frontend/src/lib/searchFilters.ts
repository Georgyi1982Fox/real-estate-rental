// Фильтры поиска: разбор адреса страницы, строка запроса для API, описание словами

import type { SearchFilters } from '../api/types';
import type { DistrictNames } from '../hooks/useDistricts';
import type { Lang, Strings } from '../i18n/strings';
import { fill, formatPrice, tr } from './format';

export const PRICE_MAX = 10000;
export const PRICE_STEP = 100;
/** «4» в фильтре означает «4 и больше» */
export const ROOMS_MAX = 4;
/** Столько районов принимает бэкенд в одном запросе */
export const DISTRICTS_MAX = 20;
/** В названии поиска по районам — первые два, остальные числом: «Ваке, Сабуртало +1» */
const DISTRICT_NAMES_SHOWN = 2;

/** Параметры адреса страницы; несколько районов — district=a,b через запятую */
export const FILTER_KEYS = ['district', 'min_price', 'max_price', 'rooms'] as const;

/** Целое число из адреса в диапазоне [min, max], иначе undefined */
function parseInteger(raw: string | null, min: number, max: number): number | undefined {
  if (raw === null || !/^\d+$/.test(raw)) return undefined;
  const value = Number(raw);
  return value >= min && value <= max ? value : undefined;
}

/** Уникальные непустые ID в исходном порядке, не больше DISTRICTS_MAX */
function uniqueIds(ids: string[]): string[] {
  const clean = ids.map((id) => id.trim()).filter(Boolean);
  return [...new Set(clean)].slice(0, DISTRICTS_MAX);
}

/**
 * Районы фильтра одним списком. Старые сохранённые поиски и ответы сервера
 * могут содержать одиночное поле district — оно тоже учитывается.
 */
export function filterDistricts(filters: SearchFilters): string[] {
  return uniqueIds([...(filters.districts ?? []), ...(filters.district ? [filters.district] : [])]);
}

/** Фильтры из адреса страницы; мусорные значения отбрасываются. Районы — всегда в districts */
export function parseFilters(params: URLSearchParams): SearchFilters {
  const filters: SearchFilters = {};
  // И ?district=a,b, и старое ?district=a&district=b
  const districts = uniqueIds(params.getAll('district').flatMap((value) => value.split(',')));
  if (districts.length > 0) filters.districts = districts;
  const minPrice = parseInteger(params.get('min_price'), 0, PRICE_MAX);
  if (minPrice !== undefined) filters.min_price = minPrice;
  const maxPrice = parseInteger(params.get('max_price'), 0, PRICE_MAX);
  if (maxPrice !== undefined) filters.max_price = maxPrice;
  const rooms = parseInteger(params.get('rooms'), 1, ROOMS_MAX);
  if (rooms !== undefined) filters.rooms = rooms;
  return filters;
}

/**
 * Только заполненные фильтры, в постоянном порядке ключей. Районы отсортированы:
 * «Ваке, Сабуртало» и «Сабуртало, Ваке» — один и тот же поиск.
 */
export function filterEntries(filters: SearchFilters): [string, string][] {
  const districts = filterDistricts(filters).sort();
  return FILTER_KEYS.flatMap((key): [string, string][] => {
    if (key === 'district') return districts.length > 0 ? [[key, districts.join(',')]] : [];
    const value = filters[key];
    return value === undefined ? [] : [[key, String(value)]];
  });
}

/** 'district=vake,saburtalo&rooms=2' — пустые значения не попадают в строку */
export function filtersToQuery(filters: SearchFilters): string {
  // Запятую не кодируем: адрес читается глазами, а бэкенд понимает оба варианта
  return new URLSearchParams(filterEntries(filters)).toString().replace(/%2C/gi, ',');
}

export function hasFilters(filters: SearchFilters): boolean {
  return filterEntries(filters).length > 0;
}

export function sameFilters(a: SearchFilters, b: SearchFilters): boolean {
  return filtersToQuery(a) === filtersToQuery(b);
}

/** Сколько фильтров выбрано: район(ы), цена, комнаты — каждый считается один раз */
export function countFilters(filters: SearchFilters): number {
  const price = filters.min_price !== undefined || filters.max_price !== undefined;
  return [filterDistricts(filters).length > 0, price, filters.rooms !== undefined].filter(Boolean)
    .length;
}

/**
 * Фильтры для POST /api/searches: один район — старое поле district (как раньше),
 * несколько — массив districts.
 */
export function toSavedFilters(filters: SearchFilters): SearchFilters {
  const { district: _district, districts: _districts, ...rest } = filters;
  const ids = filterDistricts(filters);
  if (ids.length === 1) return { ...rest, district: ids[0] };
  if (ids.length > 1) return { ...rest, districts: ids };
  return rest;
}

/** «Ваке, Сабуртало +1» по алфавиту; неизвестные ID (районы ещё грузятся) пропускаются */
export function districtsLabel(ids: string[], names: DistrictNames, lang: Lang): string {
  const collator = new Intl.Collator(lang);
  const known = ids
    .flatMap((id) => (names[id] ? [tr(names[id], lang)] : []))
    .sort(collator.compare);
  const shown = known.slice(0, DISTRICT_NAMES_SHOWN).join(', ');
  const rest = known.length - DISTRICT_NAMES_SHOWN;
  return rest > 0 ? `${shown} +${rest}` : shown;
}

/** Части описания фильтров по отдельности — для чипов и строки описания */
export interface FilterLabels {
  districts?: string;
  rooms?: string;
  price?: string;
}

export function filterLabels(
  filters: SearchFilters,
  districtNames: string,
  st: Strings['searches'],
): FilterLabels {
  const labels: FilterLabels = {};
  if (districtNames) labels.districts = districtNames;
  if (filters.rooms !== undefined) {
    const rooms = filters.rooms >= ROOMS_MAX ? `${ROOMS_MAX}+` : String(filters.rooms);
    labels.rooms = fill(st.rooms, rooms);
  }
  const { min_price: min, max_price: max } = filters;
  if (min !== undefined && max !== undefined) {
    labels.price = `${formatPrice(min, '')}–${formatPrice(max)}`;
  } else if (min !== undefined) {
    labels.price = fill(st.price_from, formatPrice(min));
  } else if (max !== undefined) {
    labels.price = fill(st.price_to, formatPrice(max));
  }
  return labels;
}

/** «Ваке, Сабуртало · 2 комн. · 800–2 000 ₾»; без фильтров — «Все квартиры» */
export function describeFilters(
  filters: SearchFilters,
  districtNames: string,
  st: Strings['searches'],
): string {
  const { districts, rooms, price } = filterLabels(filters, districtNames, st);
  const parts = [districts, rooms, price].filter(Boolean);
  return parts.length > 0 ? parts.join(' · ') : st.all;
}
