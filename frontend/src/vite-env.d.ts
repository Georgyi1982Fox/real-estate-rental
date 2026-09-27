/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Username Telegram-бота без @ (ссылка «Открыть в Telegram») */
  readonly VITE_BOT_USERNAME?: string;
  /** "true" — показать вход через Google и email в браузере (нужен бэкенд /api/auth/*) */
  readonly VITE_ENABLE_WEB_AUTH?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
