import type { Localized } from '../api/types';
import type { Lang } from '../i18n/strings';

const CURRENCY_SYMBOLS: Record<string, string> = { GEL: '₾', USD: '$', EUR: '€' };

/** Единый формат цены: '1 200 ₾' */
export function formatPrice(value: unknown, currency: string = 'GEL'): string {
  const amount = Number(value);
  const safe = Number.isFinite(amount) ? Math.round(amount) : 0;
  const digits = String(Math.abs(safe)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  const symbol = CURRENCY_SYMBOLS[currency] ?? currency;
  return `${safe < 0 ? '-' : ''}${digits}${symbol ? ` ${symbol}` : ''}`;
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
