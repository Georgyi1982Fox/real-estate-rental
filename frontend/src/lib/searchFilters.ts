// Фильтры поиска: разбор адреса страницы, строка запроса для API, описание словами

import type { District, SearchFilters } from '../api/types';
import type { CityNames } from '../hooks/useCity';
import type { DistrictNames } from '../hooks/useDistricts';
import { conditionName } from '../i18n/conditions';
import { featureName } from '../i18n/features';
import type { Lang, Strings } from '../i18n/strings';
import { fill, formatPrice, tr } from './format';

export const PRICE_MAX = 10000;
export const PRICE_STEP = 100;
/** Посуточная цена на порядок меньше помесячной — и шаг поля мельче */
export const DAILY_PRICE_STEP = 10;
/** Быстрый выбор цены за сутки: «до 80 ₾», «80–120 ₾», «120–200 ₾», «от 200 ₾» */
export const DAILY_PRICE_PRESETS: PriceBounds[] = [
  { max: 80 },
  { min: 80, max: 120 },
  { min: 120, max: 200 },
  { min: 200 },
];
/** Лента в режиме «Посуточно»: плитка главного меню и старый адрес /daily */
export const DAILY_SEARCH_PATH = '/search?rent_period=daily';

export interface PriceBounds {
  min?: number;
  max?: number;
}
/** «4» в фильтре означает «4 и больше» */
export const ROOMS_MAX = 4;
/** Столько районов принимает бэкенд в одном запросе */
export const DISTRICTS_MAX = 20;
/** В названии поиска по районам — первые два, остальные числом: «Ваке, Сабуртало +1» */
const DISTRICT_NAMES_SHOWN = 2;

export const AREA_MAX = 1000;
export const FLOOR_MAX = 100;
/** Последнее значение в спальнях и санузлах означает «и больше», как в комнатах */
export const BEDROOMS_MAX = 4;
export const BATHROOMS_MAX = 3;
/** Столько кодов удобств или состояний берём из адреса */
const CODES_MAX = 30;
const CITY_MAX = 64;
/**
 * «Вся Грузия» в адресе страницы (?city=all) и в хранилище выбранного города.
 * В запросы к API не попадает: без city сервер ищет по всей стране
 */
export const ALL_CITIES = 'all';

const NUMBER_KEYS = [
  'min_price',
  'max_price',
  'rooms',
  'min_area',
  'max_area',
  'floor_min',
  'floor_max',
  'bedrooms',
  'bathrooms',
] as const;
const FLAG_KEYS = ['not_first_floor', 'not_last_floor', 'owner_only'] as const;
/** Списки кодов: в адресе через запятую, как районы */
const LIST_KEYS = ['features', 'condition'] as const;

/** Параметры адреса страницы; несколько районов — district=a,b через запятую */
export const FILTER_KEYS = [
  'district',
  ...NUMBER_KEYS,
  ...FLAG_KEYS,
  ...LIST_KEYS,
  'city',
  'rent_period',
] as const;

/**
 * Поиск по словам: параметр адреса и запроса к API. На странице поиска живёт отдельно
 * от фильтров (useSearchFilters().query), в сохранённом поиске — поле filters.q
 */
export const QUERY_KEY = 'q';
/** Столько символов принимает бэкенд в q */
export const QUERY_MAX = 100;
/** С такой длины текста появляются подсказки районов */
export const SUGGEST_MIN_CHARS = 2;
export const SUGGEST_MAX = 6;

/** Сортировка ленты: параметр адреса и запроса к API. В сохранённый поиск не входит */
export const SORT_KEY = 'sort';
/** Что умеет GET /api/listings?sort=; без параметра сервер отдаёт newest, а при q — самые подходящие */
export const SORT_ORDERS = [
  'newest',
  'price_asc',
  'price_desc',
  'area_desc',
  'price_per_m2_asc',
] as const;
export type SortOrder = (typeof SORT_ORDERS)[number];

/** Сортировка из адреса; незнакомое значение — как будто её нет */
export function parseSort(raw: string | null): SortOrder | undefined {
  return SORT_ORDERS.find((order) => order === raw);
}

/** Целое число из адреса в диапазоне [min, max], иначе undefined */
function parseInteger(raw: string | null, min: number, max: number): number | undefined {
  if (raw === null || !/^\d+$/.test(raw)) return undefined;
  const value = Number(raw);
  return value >= min && value <= max ? value : undefined;
}

/** Уникальные непустые ID в исходном порядке, не больше limit */
function uniqueIds(ids: string[], limit = DISTRICTS_MAX): string[] {
  const clean = ids.map((id) => id.trim()).filter(Boolean);
  return [...new Set(clean)].slice(0, limit);
}

/** Границы чисел из адреса; верхнее значение комнат, спален и санузлов — «и больше» */
const NUMBER_LIMITS: Record<(typeof NUMBER_KEYS)[number], [min: number, max: number]> = {
  min_price: [0, PRICE_MAX],
  max_price: [0, PRICE_MAX],
  rooms: [1, ROOMS_MAX],
  min_area: [0, AREA_MAX],
  max_area: [0, AREA_MAX],
  floor_min: [1, FLOOR_MAX],
  floor_max: [1, FLOOR_MAX],
  bedrooms: [1, BEDROOMS_MAX],
  bathrooms: [1, BATHROOMS_MAX],
};

/**
 * Районы фильтра одним списком. Старые сохранённые поиски и ответы сервера
 * могут содержать одиночное поле district — оно тоже учитывается.
 */
export function filterDistricts(filters: SearchFilters): string[] {
  return uniqueIds([...(filters.districts ?? []), ...(filters.district ? [filters.district] : [])]);
}

/** Значения параметра списком: и ?key=a,b, и ?key=a&key=b */
function listParam(params: URLSearchParams, key: string, limit?: number): string[] {
  return uniqueIds(
    params.getAll(key).flatMap((value) => value.split(',')),
    limit,
  );
}

/**
 * Фильтры из адреса страницы; мусорные значения отбрасываются. Районы — всегда в districts.
 * Текст поиска (q) сюда не входит — см. QUERY_KEY
 */
export function parseFilters(params: URLSearchParams): SearchFilters {
  const filters: SearchFilters = {};
  const districts = listParam(params, 'district');
  if (districts.length > 0) filters.districts = districts;
  NUMBER_KEYS.forEach((key) => {
    const [min, max] = NUMBER_LIMITS[key];
    const value = parseInteger(params.get(key), min, max);
    if (value !== undefined) filters[key] = value;
  });
  FLAG_KEYS.forEach((key) => {
    const value = params.get(key);
    if (value === 'true' || value === '1') filters[key] = true;
  });
  LIST_KEYS.forEach((key) => {
    const codes = listParam(params, key, CODES_MAX);
    if (codes.length > 0) filters[key] = codes;
  });
  const city = (params.get('city') ?? '').trim().slice(0, CITY_MAX);
  if (city) filters.city = city;
  // 'monthly' — значение по умолчанию, в адресе его не держим
  if (params.get('rent_period') === 'daily') filters.rent_period = 'daily';
  return filters;
}

/** Фильтры, как их отдаёт /api/searches: незаданные поля — null */
type RawFilters = { [Key in keyof SearchFilters]?: SearchFilters[Key] | null };

/**
 * Убирает незаданные поля из ответа сервера: null, пустые строки и списки, false.
 * Остальное (в т. ч. city и rent_period) остаётся как есть.
 */
export function cleanFilters(raw: RawFilters): SearchFilters {
  const filled = Object.entries(raw).filter(
    ([, value]) =>
      value != null &&
      value !== false &&
      value !== '' &&
      !(Array.isArray(value) && value.length === 0),
  );
  return Object.fromEntries(filled) as SearchFilters;
}

/** Текст поиска без пробелов по краям, не длиннее QUERY_MAX */
export function cleanQuery(raw: string | null): string {
  return (raw ?? '').trim().slice(0, QUERY_MAX).trim();
}

/**
 * Только заполненные фильтры, в постоянном порядке ключей. Списки отсортированы:
 * «Ваке, Сабуртало» и «Сабуртало, Ваке» — один и тот же поиск.
 * Незаданным считается и то, что сервер отдаёт вместо пропуска: null, [], false,
 * rent_period: 'monthly'.
 */
export function filterEntries(filters: SearchFilters): [string, string][] {
  const entries: [string, string][] = [];
  const query = cleanQuery(filters.q ?? null);
  if (query) entries.push([QUERY_KEY, query]);
  const districts = filterDistricts(filters).sort();
  if (districts.length > 0) entries.push(['district', districts.join(',')]);
  NUMBER_KEYS.forEach((key) => {
    const value = filters[key];
    if (value != null) entries.push([key, String(value)]);
  });
  FLAG_KEYS.forEach((key) => {
    if (filters[key]) entries.push([key, 'true']);
  });
  LIST_KEYS.forEach((key) => {
    const codes = uniqueIds(filters[key] ?? [], CODES_MAX).sort();
    if (codes.length > 0) entries.push([key, codes.join(',')]);
  });
  if (filters.city) entries.push(['city', filters.city]);
  if (filters.rent_period && filters.rent_period !== 'monthly') {
    entries.push(['rent_period', filters.rent_period]);
  }
  return entries;
}

/** 'district=vake,saburtalo&rooms=2' — пустые значения не попадают в строку */
export function filtersToQuery(filters: SearchFilters): string {
  // Запятую не кодируем: адрес читается глазами, а бэкенд понимает оба варианта
  return new URLSearchParams(filterEntries(filters)).toString().replace(/%2C/gi, ',');
}

/**
 * Строка запроса для /api/listings: поиск по словам + фильтры + сортировка.
 * Без sort при q сервер сам ставит сверху самые подходящие.
 */
export function searchToQuery(filters: SearchFilters, query: string, sort?: SortOrder): string {
  const search = filtersToQuery(withQuery(filters, query));
  if (!sort) return search;
  return `${search}${search ? '&' : ''}${SORT_KEY}=${sort}`;
}

/** Фильтры страницы вместе с текстом поиска — в таком виде поиск сохраняется */
export function withQuery(filters: SearchFilters, query: string): SearchFilters {
  return { ...filters, q: query || undefined };
}

/** Город и срок аренды — режимы ленты: выбраны всегда, фильтрами не считаются и не сбрасываются */
const MODE_KEYS = ['city', 'rent_period'];

export function isDaily(filters: SearchFilters): boolean {
  return filters.rent_period === 'daily';
}

/** Город (см. useCity) и срок аренды фильтрами не считаются */
export function hasFilters(filters: SearchFilters): boolean {
  return filterEntries(filters).some(([key]) => !MODE_KEYS.includes(key));
}

export function sameFilters(a: SearchFilters, b: SearchFilters): boolean {
  return filtersToQuery(a) === filtersToQuery(b);
}

/** Фильтры, которые в счётчике идут за один: границы цены, площади, всё про этаж */
const COUNT_GROUPS: string[][] = [
  ['min_price', 'max_price'],
  ['min_area', 'max_area'],
  ['floor_min', 'floor_max', 'not_first_floor', 'not_last_floor'],
];

/**
 * Сколько фильтров выбрано: районы, удобства и состояния — по одному на список,
 * группы COUNT_GROUPS — по одному на группу. Текст поиска, город и срок аренды не считаются
 */
export function countFilters(filters: SearchFilters): number {
  const keys = filterEntries(filters).flatMap(([key]) =>
    key === QUERY_KEY || MODE_KEYS.includes(key) ? [] : [key],
  );
  const groupOf = (key: string) => COUNT_GROUPS.find((group) => group.includes(key))?.[0] ?? key;
  return new Set(keys.map(groupOf)).size;
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

/**
 * Районы для подсказок: название на любом из трёх языков содержит текст (без учёта регистра).
 * Сначала те, чьё название на языке интерфейса начинается с текста. Уже выбранные не показываем.
 */
export function suggestDistricts(
  districts: District[],
  text: string,
  lang: Lang,
  selected: string[],
): District[] {
  const needle = text.trim().toLocaleLowerCase();
  if (needle.length < SUGGEST_MIN_CHARS) return [];
  const matches = districts.filter(
    ({ id, name }) =>
      !selected.includes(id) &&
      (['ka', 'ru', 'en'] as const).some((key) =>
        tr(name, key).toLocaleLowerCase().includes(needle),
      ),
  );
  const startsWith = (district: District) =>
    tr(district.name, lang).toLocaleLowerCase().startsWith(needle);
  return [
    ...matches.filter(startsWith),
    ...matches.filter((district) => !startsWith(district)),
  ].slice(0, SUGGEST_MAX);
}

/** Части описания фильтров по отдельности — для чипов и строки описания */
export interface FilterLabels {
  districts?: string;
  rooms?: string;
  price?: string;
}

/** «800–2 000 ₾», «от 800 ₾», «до 2 000 ₾»; обе границы пустые — undefined */
export function priceLabel({ min, max }: PriceBounds, st: Strings['searches']): string | undefined {
  if (min !== undefined && max !== undefined) return `${formatPrice(min, '')}–${formatPrice(max)}`;
  if (min !== undefined) return fill(st.price_from, formatPrice(min));
  if (max !== undefined) return fill(st.price_to, formatPrice(max));
  return undefined;
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
  const price = priceLabel({ min: filters.min_price, max: filters.max_price }, st);
  if (price) labels.price = price;
  return labels;
}

/**
 * «Ваке, Сабуртало · 2 комн. · 800–2 000 ₾»; без фильтров — «Все квартиры».
 * Выбраны только дополнительные фильтры (они показаны чипами) — «Поиск по фильтрам»
 */
export function describeFilters(
  filters: SearchFilters,
  districtNames: string,
  st: Strings['searches'],
): string {
  const { districts, rooms, price } = filterLabels(filters, districtNames, st);
  const parts = [districts, rooms, price].filter(Boolean);
  if (parts.length > 0) return parts.join(' · ');
  return hasFilters(filters) ? st.custom : st.all;
}

/** Чип выбранного фильтра; patch убирает этот фильтр (нужные поля — undefined) */
export interface FilterChip {
  key: string;
  label: string;
  patch: SearchFilters;
}

/** «50–80 м²», «от 50 м²», «до 80 м²»; обе границы пустые — undefined */
function rangeText(
  min: number | undefined,
  max: number | undefined,
  st: Strings['searches'],
  unit = '',
): string | undefined {
  const withUnit = (value: number) => (unit ? `${value} ${unit}` : String(value));
  if (min != null && max != null) return `${min}–${withUnit(max)}`;
  if (min != null) return fill(st.price_from, withUnit(min));
  if (max != null) return fill(st.price_to, withUnit(max));
  return undefined;
}

/** «3» или «4+» для полей, где верхнее значение — «и больше» */
export function countText(value: number, top: number): string {
  return value >= top ? `${top}+` : String(value);
}

/**
 * Чипы дополнительных фильтров — всего, кроме районов, цены и комнат (filterLabels):
 * текст поиска, площадь, спальни, санузлы, этаж, состояние, удобства, собственник.
 * Неизвестный код удобства или состояния показывается как есть.
 * cityNames — для карточки сохранённого поиска: добавляет чипы «Посуточно» и города
 * («Батуми» или «Вся Грузия»); на странице поиска их показывают переключатель срока
 * аренды и кнопка выбора города.
 */
export function extraFilterChips(
  filters: SearchFilters,
  t: Strings,
  lang: Lang,
  cityNames?: CityNames,
): FilterChip[] {
  const ft = t.filters;
  const chips: FilterChip[] = [];
  const query = cleanQuery(filters.q ?? null);
  if (query) {
    chips.push({ key: 'q', label: fill(t.searches.query, query), patch: { q: undefined } });
  }
  const area = rangeText(filters.min_area, filters.max_area, t.searches, t.card.sqm);
  if (area) {
    chips.push({ key: 'area', label: area, patch: { min_area: undefined, max_area: undefined } });
  }
  if (filters.bedrooms != null) {
    chips.push({
      key: 'bedrooms',
      label: `${ft.bedrooms}: ${countText(filters.bedrooms, BEDROOMS_MAX)}`,
      patch: { bedrooms: undefined },
    });
  }
  if (filters.bathrooms != null) {
    chips.push({
      key: 'bathrooms',
      label: `${ft.bathrooms}: ${countText(filters.bathrooms, BATHROOMS_MAX)}`,
      patch: { bathrooms: undefined },
    });
  }
  const floor = rangeText(filters.floor_min, filters.floor_max, t.searches);
  if (floor) {
    chips.push({
      key: 'floor',
      label: `${ft.floor}: ${floor}`,
      patch: { floor_min: undefined, floor_max: undefined },
    });
  }
  if (filters.not_first_floor) {
    chips.push({
      key: 'not_first_floor',
      label: ft.not_first_floor,
      patch: { not_first_floor: undefined },
    });
  }
  if (filters.not_last_floor) {
    chips.push({
      key: 'not_last_floor',
      label: ft.not_last_floor,
      patch: { not_last_floor: undefined },
    });
  }
  // Чип на каждый код: убирается по одному
  const without = (codes: string[], code: string) => {
    const rest = codes.filter((item) => item !== code);
    return rest.length > 0 ? rest : undefined;
  };
  const conditions = uniqueIds(filters.condition ?? [], CODES_MAX);
  conditions.forEach((code) => {
    chips.push({
      key: `condition:${code}`,
      label: conditionName(code, lang) ?? code,
      patch: { condition: without(conditions, code) },
    });
  });
  const features = uniqueIds(filters.features ?? [], CODES_MAX);
  features.forEach((code) => {
    chips.push({
      key: `features:${code}`,
      label: featureName(code, lang) ?? code,
      patch: { features: without(features, code) },
    });
  });
  if (filters.owner_only) {
    chips.push({ key: 'owner_only', label: ft.owner_only, patch: { owner_only: undefined } });
  }
  if (cityNames) {
    if (isDaily(filters)) {
      chips.push({ key: 'rent_period', label: ft.daily, patch: { rent_period: undefined } });
    }
    // Название города ещё грузится или города уже нет в списке — показываем код
    const name = filters.city ? cityNames[filters.city] : undefined;
    const label = filters.city ? (name ? tr(name, lang) : filters.city) : t.city.all;
    chips.push({ key: 'city', label, patch: { city: undefined } });
  }
  return chips;
}
