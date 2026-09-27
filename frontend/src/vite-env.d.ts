/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Username Telegram-бота без @ (ссылка «Открыть в Telegram») */
  readonly VITE_BOT_USERNAME?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
