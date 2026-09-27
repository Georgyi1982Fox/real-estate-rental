import type { Lang } from '../i18n/strings';

// Текст с бэкенда: либо словарь {ka, ru, en}, либо уже готовая строка
export type Localized = Partial<Record<Lang, string>> | string;

export type Currency = 'GEL' | 'USD' | 'EUR';

export interface Owner {
  name?: Localized;
}

/** ID квартиры: UUID-строка с бэкенда, число — только в mock_data.json */
export type ListingId = string | number;

export interface Listing {
  id: ListingId;
  title: Localized;
  description?: Localized;
  price: number;
  currency: Currency | string;
  rooms: number;
  bedrooms?: number;
  area: number;
  floor?: number;
  total_floors?: number;
  deposit?: number;
  district: string;
  city?: string;
  address?: Localized;
  features?: string[];
  owner?: Owner;
  images?: string[];
  rating?: number;
  /** Есть ли телефон (GET /api/listings/{id}/phone); MyHome номера скрывает */
  has_phone?: boolean;
  /** Объявление на сайте-источнике */
  source_url?: string | null;
  /** Имя арендодателя с сайта-источника */
  owner_name?: string | null;
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
  subscription_tier: SubscriptionTier;
  subscription_expires_at: string | null;
  balance: number;
  favorites_count: number;
  created_at: string;
}

export interface UpdateMeRequest {
  language: Lang;
}
