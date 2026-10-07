import type { Lang } from '../i18n/strings';

// Текст с бэкенда: либо словарь {ka, ru, en}, либо уже готовая строка
export type Localized = Partial<Record<Lang, string>> | string;

export type Currency = 'GEL' | 'USD' | 'EUR';

export interface Owner {
  name?: Localized;
}

/** ID квартиры: UUID-строка с бэкенда, число — только в mock_data.json */
export type ListingId = string | number;

/** Проверка на мошенничество: warning — предупредить; high — скрыто из поиска, открывается по ссылке */
export type FraudLevel = 'none' | 'warning' | 'high';

/** Удобства со страницы объявления на сайте-источнике (TASK-018) */
export type FeatureCode =
  | 'furniture'
  | 'kitchen_appliances'
  | 'air_conditioning'
  | 'heating'
  | 'hot_water'
  | 'washing_machine'
  | 'dishwasher'
  | 'fridge'
  | 'tv'
  | 'internet'
  | 'gas'
  | 'elevator'
  | 'parking'
  | 'balcony'
  | 'storage'
  | 'pool'
  | 'pets_allowed'
  | 'security';

export type ConditionCode =
  | 'newly_renovated'
  | 'renovated'
  | 'needs_renovation'
  | 'under_renovation'
  | 'white_frame'
  | 'black_frame'
  | 'green_frame';

/** Кто сдаёт: собственник (в т. ч. разместил сам через бота) или агентство */
export type OwnerType = 'owner' | 'agent';

// Подробности объявления: null — сайт не указал, поля может не быть вовсе
// (объявление ещё не дозагружено) — в обоих случаях строку не показываем
export interface Listing {
  id: ListingId;
  title: Localized;
  description?: Localized;
  price: number;
  currency: Currency | string;
  rooms: number;
  bedrooms?: number | null;
  bathrooms?: number | null;
  area: number;
  floor?: number | null;
  total_floors?: number | null;
  condition?: ConditionCode | null;
  deposit?: number;
  district: string;
  city?: string;
  /** Улица на языках интерфейса; {} — сайт не указал */
  address?: Localized;
  /** Неизвестные коды не показываем */
  features?: FeatureCode[];
  owner_type?: OwnerType | null;
  latitude?: number | null;
  longitude?: number | null;
  /** Опубликовано на сайте-источнике */
  published_at?: string | null;
  /** Обновлено на сайте-источнике */
  updated_at?: string | null;
  owner?: Owner;
  images?: string[];
  rating?: number;
  /** Есть ли телефон (GET /api/listings/{id}/phone); MyHome номера скрывает */
  has_phone?: boolean;
  /**
   * Откуда объявление: 'owner' — хозяин разместил сам через бота (TASK-096),
   * остальные значения — сайты-источники
   */
  source?: string | null;
  /**
   * Объявление на сайте-источнике. У объявлений хозяина (source === 'owner') —
   * ссылка на переписку в боте: https://t.me/<бот>?start=chat_<id>
   */
  source_url?: string | null;
  /** Имя арендодателя с сайта-источника */
  owner_name?: string | null;
  fraud_level: FraudLevel;
  /** Коды причин (prepayment, off_platform, …); неизвестные коды не показываем */
  fraud_reasons: string[];
  /**
   * Та же квартира на других сайтах (TASK-090). Только в GET /api/listings/{id};
   * в списке объявлений — всегда []
   */
  also_on?: ListingSourceLink[];
}

/** Ссылка на объявление на сайте: source — ss, myhome, livo, korter, telegram */
export interface ListingSourceLink {
  source: string;
  url: string;
}

/** Цена относительно рынка; unknown — данных мало, плашку не показываем */
export type PriceLevel = 'below' | 'fair' | 'above' | 'unknown';

/** С чем сравнивали: похожие квартиры в районе или цена за м² в районе */
export type PriceBasis = 'district_rooms' | 'district_m2';

/**
 * GET /api/listings/{id}/price (нужен X-Telegram-Init-Data, иначе 401).
 * Без Premium числа — null, а premium_required: true
 */
export interface PriceEstimate {
  level: PriceLevel;
  /** Отрицательный — дешевле рынка */
  diff_percent: number | null;
  /** Обычная цена всей квартиры (не за м²) */
  typical_price: number | null;
  currency: Currency | string;
  /** По скольким объявлениям посчитано */
  sample: number | null;
  basis: PriceBasis | null;
  premium_required: boolean;
}

export interface District {
  id: string;
  name: Localized;
  /** Код города района (GET /api/cities) */
  city?: string;
}

/** GET /api/cities — только города, где уже есть объявления; список растёт сам */
export interface City {
  code: string;
  name: Localized;
  /** Центр города — для карты */
  latitude?: number | null;
  longitude?: number | null;
}

export interface ListResponse<T> {
  items: T[];
}

export interface ListingsPage extends ListResponse<Listing> {
  total: number;
  page: number;
  pages: number;
}

export interface PhoneResponse {
  phone: string;
}

// «Написать»: куда вести пользователя решает бэкенд (t.me, внешняя ссылка или внутренняя страница)
export interface ContactResponse {
  url: string;
}

/** Пользователь приложения: из Telegram (initDataUnsafe.user) или из /api/auth/me в браузере */
export interface AuthUser {
  id: number | string;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  language_code?: string;
  email?: string;
}

export interface AuthResponse {
  user: AuthUser;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest extends LoginRequest {
  first_name: string;
}

export type SubscriptionTier = 'free' | 'nomad' | 'family' | 'realtor';

/** Профиль из GET/PATCH /api/me (нужен X-Telegram-Init-Data, иначе 401). Имя и фото — из Telegram */
export interface Me {
  telegram_id: number;
  language: Lang;
  /** Тариф с учётом срока: истёкшая подписка — уже 'free' */
  subscription_tier: SubscriptionTier;
  /** Только у действующей подписки */
  subscription_expires_at: string | null;
  is_premium: boolean;
  balance: number;
  favorites_count: number;
  created_at: string;
}

/** Тарифный план для покупки звёздами Telegram */
export interface Plan {
  /** Например, "premium_month" */
  id: string;
  tier: SubscriptionTier;
  days: number;
  price_stars: number;
}

/** Лимиты тарифа; null — без ограничения */
export interface SubscriptionLimits {
  favorites: number | null;
  searches: number;
}

/** GET /api/subscription (нужен X-Telegram-Init-Data, иначе 401) */
export interface Subscription {
  /** "nomad" = Premium */
  tier: SubscriptionTier;
  is_premium: boolean;
  expires_at: string | null;
  limits: SubscriptionLimits;
  usage: { favorites: number; searches: number };
  plans: Plan[];
}

export interface InvoiceRequest {
  plan: string;
}

/** Ссылка на счёт для Telegram.WebApp.openInvoice */
export interface InvoiceResponse {
  url: string;
}

export interface UpdateMeRequest {
  language: Lang;
}

/** Фильтры поиска квартир: в адресе страницы, в /api/listings и в сохранённых поисках */
export interface SearchFilters {
  /** ID района (UUID на бэкенде). Старое поле: сервер отдаёт его, только если район ровно один */
  district?: string;
  /** Несколько районов: квартиры в любом из них (до 20) */
  districts?: string[];
  min_price?: number;
  max_price?: number;
  /** 4 = «4 и больше» */
  rooms?: number;
  min_area?: number;
  max_area?: number;
  /** Поиск по словам (строка поиска) */
  q?: string;
  floor_min?: number;
  floor_max?: number;
  not_first_floor?: boolean;
  not_last_floor?: boolean;
  bedrooms?: number;
  bathrooms?: number;
  /** Коды удобств (FeatureCode): в квартире должны быть все */
  features?: string[];
  /** Коды состояния (ConditionCode): подходит любое из выбранных */
  condition?: string[];
  owner_only?: boolean;
  /** Город (TASK-079): сервер отдаёт в сохранённых поисках, передаём как есть */
  city?: string;
  /** Срок аренды (TASK-092); 'monthly' — то же, что поле не задано */
  rent_period?: RentPeriod;
}

export type RentPeriod = 'monthly' | 'daily';

/** Сохранённый поиск (/api/searches, нужен X-Telegram-Init-Data, иначе 401) */
export interface SavedSearch {
  id: string;
  /** Если не передать при создании, сервер соберёт из фильтров: «Ваке, 2 комн., до 2000 ₾» */
  name: string;
  /** Сервер отдаёт незаданные поля как null — useSavedSearches их убирает (cleanFilters) */
  filters: SearchFilters;
  /** Присылать уведомления о новых квартирах */
  notify: boolean;
  /** Новых квартир с последнего просмотра */
  new_count: number;
  created_at: string;
}

export interface CreateSavedSearchRequest {
  name?: string;
  filters: SearchFilters;
  notify: boolean;
}

export interface UpdateSavedSearchRequest {
  name?: string;
  notify?: boolean;
}

/** Уведомление: новая квартира по сохранённому поиску, снижение цены в избранном, служебное */
export type NotificationType = 'new_listing' | 'price_drop' | 'system';

export interface NotificationListing {
  id: string;
  title: Localized;
  price: number;
  currency: string;
  image?: string | null;
}

/** Уведомление (/api/notifications, нужен X-Telegram-Init-Data, иначе 401) */
export interface AppNotification {
  id: string;
  type: NotificationType;
  created_at: string;
  is_read: boolean;
  /** Для new_listing и price_drop */
  listing?: NotificationListing | null;
  /** Для price_drop */
  old_price?: number | null;
  /** Для new_listing */
  search_id?: string | null;
  search_name?: string | null;
  /** Для system */
  text?: Localized | null;
}

export interface NotificationsPage {
  items: AppNotification[];
  total: number;
  page: number;
  pages: number;
  unread_count: number;
}

export interface UnreadCountResponse {
  count: number;
}

/** Документы сервиса: GET /api/legal/{doc}?lang= */
export type LegalDocId = 'terms' | 'privacy';

export interface LegalSection {
  title: string;
  /** Обычный текст, абзацы разделены переводом строки */
  text: string;
}

export interface LegalDocument {
  /** Нет — заголовок берём из словаря интерфейса */
  title?: string | null;
  /** «Редакция от …» */
  version_label?: string | null;
  intro?: string | null;
  sections: LegalSection[];
}

/** Причина подозрения: без Premium title и explanation — null, остаётся только код */
export interface RiskReason {
  code: string;
  title: string | null;
  explanation: string | null;
}

/**
 * GET /api/listings/{id}/risk (нужен X-Telegram-Init-Data, иначе 401).
 * Тексты уже на языке пользователя. Без Premium checklist пустой, premium_required: true
 */
export interface ListingRisk {
  level: FraudLevel;
  reasons: RiskReason[];
  /** «Что проверить до встречи»; у level: none — «Как безопасно снять квартиру» */
  checklist: string[];
  premium_required: boolean;
}

/** exact — точка известна; district — только район (показываем круг); none — карты нет */
export type LocationPrecision = 'exact' | 'district' | 'none';

/** GET /api/listings/{id}/location?lang= — работает и без входа */
export interface ListingLocation {
  precision: LocationPrecision;
  latitude: number | null;
  longitude: number | null;
  /** Название района на языке запроса */
  district: string | null;
  address: string | null;
  links?: {
    google?: string | null;
    yandex?: string | null;
    osm?: string | null;
  } | null;
}

/** Метка района; title уже на языке запроса */
export interface DistrictTag {
  code: string;
  title: string;
}

/** «Обычно: 1-комн. ~1 100 ₾»; rooms: 4 — «4 и больше» */
export interface DistrictMedianRent {
  rooms: number;
  price: number;
}

/** GET /api/districts/{id}?lang= — справка о районе, работает и без входа */
export interface DistrictInfo {
  id: string;
  /** Название на языке запроса */
  name: string;
  names: Localized;
  city: string;
  city_name: string;
  latitude: number | null;
  longitude: number | null;
  distance_km: number | null;
  minutes_to_center: number | null;
  metro: boolean | null;
  tags: DistrictTag[];
  about: string | null;
  /** Объявлений в поиске */
  listings: number;
  currency: string;
  /** Обычная аренда по числу комнат */
  median_rent: DistrictMedianRent[];
  note: string;
}
