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

// Chromium (Chrome, Edge, WebView Telegram на Android) не знает грузинского в Intl-датах
// и молча подставляет английский («August 28», «yesterday») — для ka форматируем сами
const KA_MONTHS = [
  'იანვარი',
  'თებერვალი',
  'მარტი',
  'აპრილი',
  'მაისი',
  'ივნისი',
  'ივლისი',
  'აგვისტო',
  'სექტემბერი',
  'ოქტომბერი',
  'ნოემბერი',
  'დეკემბერი',
];

function dateText(date: Date, lang: Lang, withYear: boolean): string {
  if (lang === 'ka') {
    const dayMonth = `${date.getDate()} ${KA_MONTHS[date.getMonth()] ?? ''}`;
    return withYear ? `${dayMonth}, ${date.getFullYear()}` : dayMonth;
  }
  return new Intl.DateTimeFormat(DATE_LOCALES[lang], {
    day: 'numeric',
    month: 'long',
    year: withYear ? 'numeric' : undefined,
  }).format(date);
}

/** «5 мин. назад», «вчера»: n единиц времени назад (n = 0 — «сейчас») */
function agoText(n: number, unit: 'second' | 'minute' | 'hour' | 'day', lang: Lang): string {
  if (lang === 'ka') {
    if (n === 0 || unit === 'second') return 'ახლა';
    if (unit === 'minute') return `${n} წთ წინ`;
    if (unit === 'hour') return `${n} სთ წინ`;
    if (n === 1) return 'გუშინ';
    return n === 2 ? 'გუშინწინ' : `${n} დღის წინ`;
  }
  return new Intl.RelativeTimeFormat(DATE_LOCALES[lang], {
    numeric: 'auto',
    style: 'short',
  }).format(-n, unit);
}

/** Дата вида '27 сентября 2026 г.' на языке интерфейса; невалидная строка — '' */
export function formatDate(iso: string, lang: Lang): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return dateText(date, lang, true);
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
  // Часы сервера могут спешить — будущее время показываем как «сейчас»
  const diff = Math.max(0, now.getTime() - date.getTime());
  if (diff < MINUTE) return agoText(0, 'second', lang);
  if (diff < HOUR) return agoText(Math.floor(diff / MINUTE), 'minute', lang);
  const days = Math.round((startOfDay(now) - startOfDay(date)) / DAY);
  if (days === 0) return agoText(Math.floor(diff / HOUR), 'hour', lang);
  if (days < 7) return agoText(days, 'day', lang);
  return formatDate(iso, lang);
}

/**
 * Когда объявление опубликовано/обновлено: сегодня от часа и больше — «01:25 ч назад»
 * (шаблон hoursAgo из словаря), меньше часа и до недели — как timeAgo, старше — «31 августа».
 * Невалидная строка — ''.
 */
export function listingTime(
  iso: string,
  lang: Lang,
  hoursAgo: string,
  now: Date = new Date(),
): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const diff = Math.max(0, now.getTime() - date.getTime());
  const days = Math.round((startOfDay(now) - startOfDay(date)) / DAY);
  if (days <= 0 && diff >= HOUR) {
    const hours = String(Math.floor(diff / HOUR)).padStart(2, '0');
    const minutes = String(Math.floor((diff % HOUR) / MINUTE)).padStart(2, '0');
    return fill(hoursAgo, `${hours}:${minutes}`);
  }
  if (days < 7) return timeAgo(iso, lang, now);
  // Год — только если он не текущий: «31 августа», но «31 августа 2025 г.»
  return dateText(date, lang, date.getFullYear() !== now.getFullYear());
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
