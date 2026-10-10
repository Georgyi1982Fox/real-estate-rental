// Названия по кодам GET /api/hotels/options (TASK-120, бэкенд application/hotels.py):
// тип объекта, тип номера, удобства.
// Отдельным файлом, как i18n/features.ts. Неизвестный код не показывается.

import type { Lang } from './strings';

type Names = Record<Lang, Record<string, string>>;

const KINDS: Names = {
  ka: {
    hotel: 'სასტუმრო',
    guesthouse: 'საოჯახო სასტუმრო',
    hostel: 'ჰოსტელი',
    apart_hotel: 'აპარტ-ოტელი',
  },
  ru: {
    hotel: 'Гостиница',
    guesthouse: 'Гостевой дом',
    hostel: 'Хостел',
    apart_hotel: 'Апарт-отель',
  },
  en: {
    hotel: 'Hotel',
    guesthouse: 'Guest house',
    hostel: 'Hostel',
    apart_hotel: 'Aparthotel',
  },
};

const ROOM_KINDS: Names = {
  ka: {
    single: 'ერთადგილიანი',
    double: 'ორადგილიანი',
    twin: 'ორი საწოლით',
    triple: 'სამადგილიანი',
    family: 'საოჯახო',
    suite: 'ლუქსი',
    dorm: 'საწოლი საერთო ოთახში',
  },
  ru: {
    single: 'Одноместный',
    double: 'Двухместный',
    twin: 'С двумя кроватями',
    triple: 'Трёхместный',
    family: 'Семейный',
    suite: 'Люкс',
    dorm: 'Место в общем номере',
  },
  en: {
    single: 'Single',
    double: 'Double',
    twin: 'Twin',
    triple: 'Triple',
    family: 'Family',
    suite: 'Suite',
    dorm: 'Dorm bed',
  },
};

const AMENITIES: Names = {
  ka: {
    wifi: 'Wi-Fi',
    parking: 'პარკინგი',
    breakfast: 'საუზმე',
    air_conditioning: 'კონდიციონერი',
    kitchen: 'სამზარეულო',
    pool: 'აუზი',
    restaurant: 'რესტორანი',
    spa: 'სპა',
    gym: 'სპორტდარბაზი',
    airport_transfer: 'ტრანსფერი აეროპორტიდან',
    reception_24h: 'მიმღები 24/7',
    pets_allowed: 'შინაური ცხოველები დაშვებულია',
    family_rooms: 'საოჯახო ნომრები',
    sea_view: 'ხედი ზღვაზე',
    mountain_view: 'ხედი მთებზე',
    elevator: 'ლიფტი',
  },
  ru: {
    wifi: 'Wi-Fi',
    parking: 'Парковка',
    breakfast: 'Завтрак',
    air_conditioning: 'Кондиционер',
    kitchen: 'Кухня',
    pool: 'Бассейн',
    restaurant: 'Ресторан',
    spa: 'Спа',
    gym: 'Спортзал',
    airport_transfer: 'Трансфер из аэропорта',
    reception_24h: 'Ресепшен 24/7',
    pets_allowed: 'Можно с животными',
    family_rooms: 'Семейные номера',
    sea_view: 'Вид на море',
    mountain_view: 'Вид на горы',
    elevator: 'Лифт',
  },
  en: {
    wifi: 'Wi-Fi',
    parking: 'Parking',
    breakfast: 'Breakfast',
    air_conditioning: 'Air conditioning',
    kitchen: 'Kitchen',
    pool: 'Pool',
    restaurant: 'Restaurant',
    spa: 'Spa',
    gym: 'Gym',
    airport_transfer: 'Airport transfer',
    reception_24h: '24/7 front desk',
    pets_allowed: 'Pets allowed',
    family_rooms: 'Family rooms',
    sea_view: 'Sea view',
    mountain_view: 'Mountain view',
    elevator: 'Elevator',
  },
};

/** Коды на случай, если /api/hotels/options не ответил: фильтры всё равно работают */
export const HOTEL_KIND_CODES = Object.keys(KINDS.ka);
export const HOTEL_AMENITY_CODES = Object.keys(AMENITIES.ka);
export const HOTEL_ROOM_KIND_CODES = Object.keys(ROOM_KINDS.ka);

const nameOf =
  (names: Names) =>
  (code: string | null | undefined, lang: Lang): string | undefined =>
    code ? (names[lang] ?? names.ru)[code] : undefined;

/** Тип объекта на языке интерфейса; undefined — код неизвестен */
export const hotelKindName = nameOf(KINDS);
export const roomKindName = nameOf(ROOM_KINDS);
export const hotelAmenityName = nameOf(AMENITIES);

/** Коды с бэкенда, для которых есть название, — в порядке бэкенда */
export function knownCodes(
  codes: string[] | undefined,
  fallback: string[],
  name: (code: string, lang: Lang) => string | undefined,
): string[] {
  const known = (codes ?? []).filter((code) => name(code, 'ka') !== undefined);
  return known.length > 0 ? known : fallback;
}
