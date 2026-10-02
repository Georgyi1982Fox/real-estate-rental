// Настройки из .env (VITE_*) с безопасными значениями по умолчанию

const BOT_USERNAME = (import.meta.env.VITE_BOT_USERNAME || 'rental_ge_bot').replace(/^@/, '');

/**
 * Вход в обычном браузере (Google, email). Бэкенд для него ещё не сделан
 * (/api/auth/* отвечает 404), поэтому по умолчанию выключен: VITE_ENABLE_WEB_AUTH=true.
 */
export const WEB_AUTH_ENABLED = import.meta.env.VITE_ENABLE_WEB_AUTH === 'true';

/** Ссылка на бота: открывает Mini App в Telegram */
export const BOT_URL = `https://t.me/${BOT_USERNAME}`;

/** Разделы бота, которые он открывает сразу по ссылке ?start=<раздел> */
export type BotSection =
  | 'search'
  | 'daily'
  | 'smart'
  | 'fav'
  | 'owner'
  | 'premium'
  | 'invite'
  | 'rent'
  | 'profile'
  | 'help'
  | 'support'
  | 'terms'
  | 'privacy';

/** Ссылка на раздел бота: https://t.me/<бот>?start=rent */
export function botSectionUrl(section: BotSection): string {
  return `${BOT_URL}?start=${section}`;
}

/** Корень приложения с учётом base (/real-estate-rental/ на GitHub Pages) */
export const APP_BASE = import.meta.env.BASE_URL;

export const LOGO_URL = `${APP_BASE}static/images/logo.svg`;
