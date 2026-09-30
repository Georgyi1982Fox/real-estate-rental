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

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** Полночь локального дня — для «вчера» считаем календарные дни, а не 24 часа */
function startOfDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

/**
 * Относительное время на языке интерфейса: «сейчас», «5 мин. назад», «3 ч. назад»,
 * «вчера», «4 дня назад»; старше недели — обычная дата. Невалидная строка — ''.
 */
export function timeAgo(iso: string, lang: Lang, now: Date = new Date()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const rtf = new Intl.RelativeTimeFormat(DATE_LOCALES[lang], { numeric: 'auto', style: 'short' });
  // Часы сервера могут спешить — будущее время показываем как «сейчас»
  const diff = Math.max(0, now.getTime() - date.getTime());
  if (diff < MINUTE) return rtf.format(0, 'second');
  if (diff < HOUR) return rtf.format(-Math.floor(diff / MINUTE), 'minute');
  const days = Math.round((startOfDay(now) - startOfDay(date)) / DAY);
  if (days === 0) return rtf.format(-Math.floor(diff / HOUR), 'hour');
  if (days < 7) return rtf.format(-days, 'day');
  return formatDate(iso, lang);
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

/** Подстановка именованных полей: fillVars('{old} → {price}', { old: '1 ₾', price: '2 ₾' }) */
export function fillVars(template: string, values: Record<string, number | string>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in values ? String(values[key]) : match,
  );
}

/** Формы слова для Intl.PluralRules: ru — one/few/many, ka и en — one/other */
export type PluralForms = Record<'one' | 'few' | 'many' | 'other', string>;

/** «Показать 1 квартиру / 3 квартиры / 5 квартир» — форма по правилам языка, {n} подставляется */
export function plural(forms: PluralForms, n: number, lang: Lang): string {
  const category = new Intl.PluralRules(DATE_LOCALES[lang]).select(n);
  const form = category in forms ? forms[category as keyof PluralForms] : forms.other;
  return fill(form, n);
}
