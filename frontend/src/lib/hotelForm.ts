// Форма размещения гостиницы: черновик, проверки шагов, тело запроса, разбор ошибок сервера

import { ApiError } from '../api/client';
import type { HotelInput, HotelRoomInput, MyHotel } from '../api/types';
import type { Strings } from '../i18n/strings';
import { fill } from './format';

/** Ограничения бэкенда (application/hotels.py) */
export const HOTEL_NAME_MIN = 2;
export const HOTEL_NAME_MAX = 120;
export const HOTEL_ADDRESS_MAX = 200;
export const HOTEL_DESCRIPTION_MIN = 30;
export const HOTEL_DESCRIPTION_MAX = 3000;
export const HOTEL_ROOMS_MAX = 30;
export const HOTEL_PHOTOS_MAX = 20;
export const HOTEL_PHOTO_MAX_BYTES = 15 * 1024 * 1024;
export const ROOM_GUESTS_MAX = 20;
export const ROOM_COUNT_MAX = 500;
export const ROOM_TITLE_MAX = 120;
/** Цена ночи: от 10 до 5 000 ₾ (в долларах и евро — по примерному курсу сервера) */
export const NIGHT_PRICE_MIN = 10;
export const NIGHT_PRICE_MAX = 5000;
const ROUGH_GEL_RATE: Record<string, number> = { GEL: 1, USD: 2.7, EUR: 3 };
/** Грузия с запасом: точку вне этих границ сервер не примет */
const GEORGIA_BOUNDS = { lat: [41.0, 43.7], lon: [39.9, 46.8] } as const;
const PHONE_RE = /^\+?\d{6,15}$/;

export const HOTEL_FORM_STEPS = [
  'main',
  'place',
  'details',
  'description',
  'rooms',
  'contacts',
  'photos',
] as const;
export type HotelFormStep = (typeof HOTEL_FORM_STEPS)[number];

/** Черновик формы: всё, что вводит хозяин; пустые строки — «не указано» */
export interface HotelDraft {
  kind: string;
  name: string;
  city: string;
  address: string;
  latitude: number | null;
  longitude: number | null;
  stars: number | null;
  amenities: string[];
  check_in: string;
  check_out: string;
  description: string;
  rooms: HotelRoomInput[];
  phone: string;
  whatsapp: string;
}

export function emptyDraft(city: string): HotelDraft {
  return {
    kind: '',
    name: '',
    city,
    address: '',
    latitude: null,
    longitude: null,
    stars: null,
    amenities: [],
    check_in: '',
    check_out: '',
    description: '',
    rooms: [],
    phone: '',
    whatsapp: '',
  };
}

/** Описание хозяина: на языке интерфейса, иначе на том, на котором оно написано */
function ownDescription(hotel: MyHotel, lang: string): string {
  const { description } = hotel;
  if (!description) return '';
  if (typeof description === 'string') return description;
  const texts = description as Record<string, string | undefined>;
  return texts[lang] || texts.ka || texts.ru || texts.en || '';
}

/** Черновик из уже размещённого объекта («Изменить») */
export function draftFromHotel(hotel: MyHotel, lang: string): HotelDraft {
  return {
    kind: hotel.kind,
    name: typeof hotel.name === 'string' ? hotel.name : '',
    city: hotel.city,
    address: hotel.address ?? '',
    latitude: hotel.latitude ?? null,
    longitude: hotel.longitude ?? null,
    stars: hotel.stars ?? null,
    amenities: hotel.amenities ?? [],
    check_in: hotel.check_in ?? '',
    check_out: hotel.check_out ?? '',
    description: ownDescription(hotel, lang),
    rooms: (hotel.rooms ?? []).map((room) => ({
      kind: room.kind,
      title: room.title ?? '',
      guests: room.guests,
      price: room.price,
      currency: room.currency,
      count: room.count,
    })),
    phone: hotel.phone ?? '',
    whatsapp: hotel.whatsapp ?? '',
  };
}

/** Телефон без пробелов, скобок и дефисов — как его чистит сервер */
export function compactPhone(text: string): string {
  return text.replace(/[\s()-]/g, '');
}

export function isPhone(text: string): boolean {
  return PHONE_RE.test(compactPhone(text));
}

export function inGeorgia(latitude: number, longitude: number): boolean {
  const { lat, lon } = GEORGIA_BOUNDS;
  return latitude >= lat[0] && latitude <= lat[1] && longitude >= lon[0] && longitude <= lon[1];
}

/** Цена ночи в лари по примерному курсу — та же проверка, что на сервере */
export function isNightPrice(price: number, currency: string): boolean {
  const gel = price * (ROUGH_GEL_RATE[currency] ?? 1);
  return gel >= NIGHT_PRICE_MIN && gel <= NIGHT_PRICE_MAX;
}

/** Тело POST / PUT /api/my/hotels */
export function toHotelInput(draft: HotelDraft): HotelInput {
  const phone = compactPhone(draft.phone);
  const whatsapp = compactPhone(draft.whatsapp);
  const hasPoint = draft.latitude !== null && draft.longitude !== null;
  return {
    kind: draft.kind,
    name: draft.name.trim(),
    city: draft.city,
    description: draft.description.trim(),
    address: draft.address.trim() || null,
    latitude: hasPoint ? draft.latitude : null,
    longitude: hasPoint ? draft.longitude : null,
    stars: draft.stars,
    amenities: draft.amenities,
    check_in: draft.check_in || null,
    check_out: draft.check_out || null,
    phone: phone || null,
    whatsapp: whatsapp || null,
    rooms: draft.rooms,
  };
}

/**
 * Что мешает уйти с шага: тексты подсказок (пусто — шаг заполнен).
 * hasTelegram — у хозяина есть имя в Telegram: тогда телефон необязателен
 */
export function stepProblems(
  step: HotelFormStep,
  draft: HotelDraft,
  ft: Strings['hotel_form'],
  hasTelegram: boolean,
): string[] {
  const problems: string[] = [];
  if (step === 'main') {
    if (!draft.kind) problems.push(ft.need_kind);
    if (draft.name.trim().length < HOTEL_NAME_MIN) problems.push(ft.need_name);
  }
  if (step === 'place') {
    if (!draft.city) problems.push(ft.need_city);
    if (
      draft.latitude !== null &&
      draft.longitude !== null &&
      !inGeorgia(draft.latitude, draft.longitude)
    ) {
      problems.push(ft.errors.point);
    }
  }
  if (step === 'description' && draft.description.trim().length < HOTEL_DESCRIPTION_MIN) {
    problems.push(ft.errors.bad_description);
  }
  if (step === 'rooms' && draft.rooms.length === 0) problems.push(ft.need_room);
  if (step === 'contacts') {
    if (draft.phone.trim() ? !isPhone(draft.phone) : !hasTelegram) {
      problems.push(draft.phone.trim() ? ft.errors.phone : ft.need_phone);
    }
    if (draft.whatsapp.trim() && !isPhone(draft.whatsapp)) problems.push(ft.errors.whatsapp);
  }
  return problems;
}

/** Причины отказа проверки правилами: «rejected: link_in_text,bad_price» */
const REJECTED_PREFIX = 'rejected:';
const REJECT_CODES = [
  'link_in_text',
  'contact_in_text',
  'bad_description',
  'bad_name',
  'bad_price',
] as const;

/** Что сервер пишет в detail → ключ текста в словаре */
const DETAIL_ERRORS: [needle: string, key: keyof Strings['hotel_form']['errors']][] = [
  ['phone is required', 'no_contact'],
  ['phone looks invalid', 'phone'],
  ['whatsapp looks invalid', 'whatsapp'],
  ['point must be in Georgia', 'point'],
  ['latitude and longitude', 'point'],
  ['unknown city', 'city'],
  ['too_many_rooms', 'too_many_rooms'],
  ['too_many_photos', 'too_many_photos'],
  ['bad_photo', 'bad_photo'],
  ['photo must be', 'bad_photo'],
];

/**
 * Ошибка сервера по-человечески: 409 — уже 5 включённых объектов, 429 — лимит на сегодня,
 * 422 «rejected: <коды>» — по тексту на каждый код, остальные 422 — по сообщению detail.
 * Незнакомая ошибка — общий текст
 */
export function hotelErrorTexts(error: unknown, ft: Strings['hotel_form'], limit: number): string[] {
  const et = ft.errors;
  if (!(error instanceof ApiError)) return [et.generic];
  if (error.isUnauthorized) return [et.login];
  if (error.status === 409) return [fill(et.limit, limit)];
  if (error.status === 429) return [et.daily];
  const detail = error.detail ?? '';
  if (detail.startsWith(REJECTED_PREFIX)) {
    const codes = detail
      .slice(REJECTED_PREFIX.length)
      .split(',')
      .map((code) => code.trim());
    const texts = REJECT_CODES.filter((code) => codes.includes(code)).map((code) => et[code]);
    return texts.length > 0 ? texts : [et.generic];
  }
  const known = DETAIL_ERRORS.find(([needle]) => detail.includes(needle));
  return [known ? et[known[1]] : et.generic];
}
