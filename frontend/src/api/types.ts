import type { Lang } from '../i18n/strings';

// Текст с бэкенда: либо словарь {ka, ru, en}, либо уже готовая строка
export type Localized = Partial<Record<Lang, string>> | string;

export type Currency = 'GEL' | 'USD' | 'EUR';

export interface Owner {
  name?: Localized;
}

export interface Listing {
  id: number;
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
