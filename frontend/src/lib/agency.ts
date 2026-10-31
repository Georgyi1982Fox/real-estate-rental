// Кабинет риелтора / агентства: адреса, ограничения полей, суммы статистики, разбор ошибок

import { ApiError } from '../api/client';
import type { AgencyListingStats, ListingShare } from '../api/types';
import type { Strings } from '../i18n/strings';
import { APP_BASE } from './config';

/** Свой кабинет */
export const AGENCY_PATH = '/agency';
export const AGENCY_API = '/api/agency';

/** Ограничения бэкенда (application/agencies.py, api/routes/agency.py) */
export const AGENCY_NAME_MIN = 2;
export const AGENCY_NAME_MAX = 80;
export const AGENCY_DESCRIPTION_MAX = 1000;
export const AGENCY_PHONE_MAX = 30;
export const AGENCY_LOGO_MAX_BYTES = 15 * 1024 * 1024;
/** До регистрации сервер лимит не сообщает; значение по умолчанию AGENCY_FREE_LISTINGS */
export const AGENCY_FREE_LISTINGS = 10;

/** Страница агентства: открывается по ссылке без входа */
export function agencyPagePath(id: string): string {
  return `${AGENCY_PATH}/${encodeURIComponent(id)}`;
}

/** Название без лишних пробелов — так его сохранит сервер */
export function cleanAgencyName(name: string): string {
  return name.trim().replace(/\s+/g, ' ');
}

export function isAgencyName(name: string): boolean {
  const { length } = cleanAgencyName(name);
  return length >= AGENCY_NAME_MIN && length <= AGENCY_NAME_MAX;
}

export interface AgencyTotals {
  views: number;
  contacts: number;
  chats: number;
  viewings: number;
}

/** Крупные цифры кабинета: суммы по всем объявлениям за 30 дней */
export function agencyTotals(items: AgencyListingStats[]): AgencyTotals {
  return items.reduce<AgencyTotals>(
    (sum, item) => ({
      views: sum.views + item.views,
      contacts: sum.contacts + item.contacts,
      chats: sum.chats + item.chats,
      viewings: sum.viewings + item.viewings,
    }),
    { views: 0, contacts: 0, chats: 0, viewings: 0 },
  );
}

/** Ссылка на страницу агентства: у API её нет, адрес собирается из адреса приложения */
export function agencyShare(id: string, text: string): ListingShare {
  const url = `${window.location.origin}${APP_BASE}${agencyPagePath(id).slice(1)}`;
  const query = new URLSearchParams({ url, text });
  return { url, text, telegram_url: `https://t.me/share/url?${query.toString()}` };
}

/** Что сервер пишет в detail → ключ текста в словаре */
const DETAIL_ERRORS: [needle: string, key: keyof Strings['agency']['errors']][] = [
  ['name must be', 'name'],
  ['phone looks invalid', 'phone'],
  ['bad_photo', 'not_photo'],
  ['logo must be', 'photo_size'],
];

/** Ошибка сервера по-человечески; незнакомая — общий текст */
export function agencyErrorText(error: unknown, at: Strings['agency']): string {
  const et = at.errors;
  if (!(error instanceof ApiError)) return et.generic;
  if (error.isUnauthorized) return et.login;
  if (error.status === 409) return et.exists;
  if (error.status === 429) return et.busy;
  const detail = error.detail ?? '';
  const known = DETAIL_ERRORS.find(([needle]) => detail.includes(needle));
  if (known) return et[known[1]];
  if (error.fields.includes('name')) return et.name;
  if (error.fields.includes('phone')) return et.phone;
  return et.generic;
}
