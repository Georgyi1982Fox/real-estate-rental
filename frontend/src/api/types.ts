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
  /** Объявление на сайте-источнике */
  source_url?: string | null;
  /** Имя арендодателя с сайта-источника */
  owner_name?: string | null;
  fraud_level: FraudLevel;
  /** Коды причин (prepayment, off_platform, …); неизвестные коды не показываем */
  fraud_reasons: string[];
}

export interface District {
  id: string;
  name: Localized;
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
}

/** Сохранённый поиск (/api/searches, нужен X-Telegram-Init-Data, иначе 401) */
export interface SavedSearch {
  id: string;
  /** Если не передать при создании, сервер соберёт из фильтров: «Ваке, 2 комн., до 2000 ₾» */
  name: string;
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
