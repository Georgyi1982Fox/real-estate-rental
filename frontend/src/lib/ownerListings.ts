// «Сдать квартиру»: адреса, черновик формы, проверки шагов, тело запроса, разбор ошибок сервера

import { ApiError } from '../api/client';
import type { Currency, OwnerListingInput, RentPeriod } from '../api/types';
import type { Strings } from '../i18n/strings';
import { fill } from './format';
import { compactPhone, inGeorgia, isPhone } from './hotelForm';

/** «Мои объявления» */
export const MY_LISTINGS_PATH = '/my-listings';
/** Форма размещения */
export const NEW_LISTING_PATH = '/my-listings/new';

/** Ограничения бэкенда (application/owner_listings.py, api/schemas.py) */
export const LISTING_DISTRICT_MIN = 2;
export const LISTING_DISTRICT_MAX = 60;
export const LISTING_ADDRESS_MAX = 150;
export const LISTING_DESCRIPTION_MIN = 20;
export const LISTING_DESCRIPTION_MAX = 3000;
export const LISTING_PHOTOS_MAX = 10;
export const LISTING_PHOTO_MAX_BYTES = 15 * 1024 * 1024;
export const LISTING_PRICE_MAX = 1_000_000;
const AREA_MIN = 10;
const AREA_MAX = 1000;
const FLOOR_MAX = 60;
/** Сколько активных объявлений можно держать, пока сервер не сказал точнее */
export const DEFAULT_LISTINGS_LIMIT = 5;

/** Кнопки комнат — как в боте: 1 / студия … 5+ */
export const LISTING_ROOMS = [1, 2, 3, 4, 5] as const;
export const LISTING_CURRENCIES: Currency[] = ['GEL', 'USD', 'EUR'];
export const CURRENCY_LABELS: Record<string, string> = {
  GEL: '₾ GEL',
  USD: '$ USD',
  EUR: '€ EUR',
};

/** Объявление создаётся на шаге «Контакты», фото добавляются уже к созданному */
export const LISTING_FORM_STEPS = ['place', 'flat', 'about', 'contact', 'photos'] as const;
export type ListingFormStep = (typeof LISTING_FORM_STEPS)[number];

/** Черновик формы: числа — текстом, как в полях; пустая строка — «не указано» */
export interface ListingDraft {
  city: string;
  district: string;
  address: string;
  latitude: number | null;
  longitude: number | null;
  rent_period: RentPeriod;
  rooms: number | null;
  area: string;
  price: string;
  currency: Currency;
  floor: string;
  total_floors: string;
  description: string;
  features: string[];
  phone: string;
}

export function emptyListingDraft(city: string): ListingDraft {
  return {
    city,
    district: '',
    address: '',
    latitude: null,
    longitude: null,
    rent_period: 'monthly',
    rooms: null,
    area: '',
    price: '',
    currency: 'GEL',
    floor: '',
    total_floors: '',
    description: '',
    features: [],
    phone: '',
  };
}

export function isListingPrice(price: number): boolean {
  return price > 0 && price <= LISTING_PRICE_MAX;
}

function isFloor(value: number, min: number): boolean {
  return Number.isInteger(value) && value >= min && value <= FLOOR_MAX;
}

/** Тело POST /api/my/listings */
export function toListingInput(draft: ListingDraft): OwnerListingInput {
  const hasPoint = draft.latitude !== null && draft.longitude !== null;
  return {
    city: draft.city,
    district: draft.district.trim(),
    rent_period: draft.rent_period,
    price: Number(draft.price),
    currency: draft.currency,
    rooms: draft.rooms ?? 1,
    area: Number(draft.area),
    floor: draft.floor === '' ? null : Number(draft.floor),
    total_floors: draft.total_floors === '' ? null : Number(draft.total_floors),
    description: draft.description.trim(),
    phone: compactPhone(draft.phone) || null,
    features: draft.features,
    address: draft.address.trim() || null,
    latitude: hasPoint ? draft.latitude : null,
    longitude: hasPoint ? draft.longitude : null,
  };
}

/**
 * Что мешает уйти с шага: тексты подсказок (пусто — шаг заполнен).
 * hasTelegram — у хозяина есть имя в Telegram: тогда телефон необязателен
 */
export function listingStepProblems(
  step: ListingFormStep,
  draft: ListingDraft,
  ft: Strings['listing_form'],
  hasTelegram: boolean,
): string[] {
  const problems: string[] = [];
  if (step === 'place') {
    if (!draft.city) problems.push(ft.need_city);
    if (draft.district.trim().length < LISTING_DISTRICT_MIN) problems.push(ft.need_district);
    if (
      draft.latitude !== null &&
      draft.longitude !== null &&
      !inGeorgia(draft.latitude, draft.longitude)
    ) {
      problems.push(ft.errors.point);
    }
  }
  if (step === 'flat') {
    const area = Number(draft.area);
    if (draft.rooms === null) problems.push(ft.need_rooms);
    if (draft.area === '' || !(area >= AREA_MIN && area <= AREA_MAX)) problems.push(ft.need_area);
    if (draft.price === '' || !isListingPrice(Number(draft.price))) problems.push(ft.need_price);
    const floor = draft.floor === '' ? null : Number(draft.floor);
    const total = draft.total_floors === '' ? null : Number(draft.total_floors);
    const badFloor =
      (floor !== null && !isFloor(floor, 0)) ||
      (total !== null && !isFloor(total, 1)) ||
      (floor !== null && total !== null && floor > total);
    if (badFloor) problems.push(ft.need_floor);
  }
  if (step === 'about' && draft.description.trim().length < LISTING_DESCRIPTION_MIN) {
    problems.push(ft.errors.bad_description);
  }
  if (step === 'contact' && (draft.phone.trim() ? !isPhone(draft.phone) : !hasTelegram)) {
    problems.push(draft.phone.trim() ? ft.errors.phone : ft.errors.no_contact);
  }
  return problems;
}

/** Что сервер пишет в detail → ключ текста в словаре */
const DETAIL_ERRORS: [needle: string, key: keyof Strings['listing_form']['errors']][] = [
  ['phone is required', 'no_contact'],
  ['phone looks invalid', 'phone'],
  ['too_many_photos', 'too_many_photos'],
  ['bad_photo', 'not_photo'],
  ['photo must be', 'photo_size'],
];

/**
 * Ошибка сервера по-человечески: 409 — уже `limit` объявлений в поиске, 429 — лимит новых
 * на сегодня, 422 — по сообщению detail или по полю. Незнакомая ошибка — общий текст
 */
export function listingErrorText(
  error: unknown,
  ft: Strings['listing_form'],
  limit: number,
): string {
  const et = ft.errors;
  if (!(error instanceof ApiError)) return et.generic;
  if (error.isUnauthorized) return et.login;
  if (error.status === 409) return fill(et.limit, limit);
  if (error.status === 429) return et.daily;
  const detail = error.detail ?? '';
  const known = DETAIL_ERRORS.find(([needle]) => detail.includes(needle));
  if (known) return et[known[1]];
  if (error.fields.includes('description')) return et.bad_description;
  return et.generic;
}
