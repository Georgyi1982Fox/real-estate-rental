import type { Localized } from '../api/types';
import type { Lang } from '../i18n/strings';

const CURRENCY_SYMBOLS: Record<string, string> = { GEL: '₾', USD: '$', EUR: '€' };

const DATE_LOCALES: Record<Lang, string> = { ka: 'ka-GE', ru: 'ru-RU', en: 'en-GB' };

function groupDigits(digits: string): string {
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

function withSymbol(amount: string, currency: string): string {
  const symbol = CURRENCY_SYMBOLS[currency] ?? currency;
  return `${amount}${symbol ? ` ${symbol}` : ''}`;
}

/** Единый формат цены: '1 200 ₾' */
export function formatPrice(value: unknown, currency: string = 'GEL'): string {
  const amount = Number(value);
  const safe = Number.isFinite(amount) ? Math.round(amount) : 0;
  const digits = groupDigits(String(Math.abs(safe)));
  return withSymbol(`${safe < 0 ? '-' : ''}${digits}`, currency);
}

/** Деньги с копейками, если они есть: '0 ₾', '12.50 ₾', '1 200 ₾' */
export function formatMoney(value: unknown, currency: string = 'GEL'): string {
  const amount = Number(value);
  const safe = Number.isFinite(amount) ? amount : 0;
  const [whole = '0', cents = '00'] = Math.abs(safe).toFixed(2).split('.');
  const sign = safe < 0 && Number(`${whole}.${cents}`) > 0 ? '-' : '';
  return withSymbol(`${sign}${groupDigits(whole)}${cents === '00' ? '' : `.${cents}`}`, currency);
}

/** Дата вида '27 сентября 2026 г.' на языке интерфейса; невалидная строка — '' */
export function formatDate(iso: string, lang: Lang): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(DATE_LOCALES[lang], {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date);
}

/** Локализованное значение из {ka, ru, en} с фолбэком ka → en → ru; строки возвращаются как есть */
export function tr(value: Localized | null | undefined, lang: Lang): string {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  return value[lang] || value.ka || value.en || value.ru || '';
}

/** Подстановка {n} в строку словаря */
export function fill(template: string, n: number | string): string {
  return template.replace('{n}', String(n));
}
