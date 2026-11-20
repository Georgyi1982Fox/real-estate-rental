// Словарь интерфейса (FRONTEND-054): по файлу на язык — ka.ts, ru.ts, en.ts.
// ka — язык по умолчанию, он в основной части сайта; ru и en — отдельные части,
// скачиваются, только когда нужны. Тип Strings выводится из ka: ru/en обязаны иметь
// те же ключи (проверяет TypeScript).

import ka from './ka';

export const LANGUAGES = [
  { code: 'ka', label: 'ქართული' },
  { code: 'ru', label: 'Русский' },
  { code: 'en', label: 'English' },
] as const;

export type Lang = (typeof LANGUAGES)[number]['code'];

export type Strings = typeof ka;

export const DEFAULT_LANG = 'ka' satisfies Lang;

/** Словарь языка по умолчанию — есть всегда, без скачивания */
export const DEFAULT_STRINGS: Strings = ka;

const LOADERS: Record<Exclude<Lang, typeof DEFAULT_LANG>, () => Promise<{ default: Strings }>> = {
  ru: () => import('./ru'),
  en: () => import('./en'),
};

const loaded: Partial<Record<Lang, Strings>> = { ka };
const pending: Partial<Record<Lang, Promise<Strings>>> = {};

/** Словарь, если он уже скачан (ka — всегда) */
export function loadedStrings(lang: Lang): Strings | undefined {
  return loaded[lang];
}

/**
 * Скачать словарь языка. Не пришёл — ещё одна попытка; не пришёл и после неё —
 * ошибка (что делать дальше, решает I18nProvider).
 */
export function loadStrings(lang: Lang): Promise<Strings> {
  const ready = loaded[lang];
  if (ready) return Promise.resolve(ready);
  if (lang === DEFAULT_LANG) return Promise.resolve(DEFAULT_STRINGS);
  const existing = pending[lang];
  if (existing) return existing;

  const load = LOADERS[lang];
  const promise = load()
    .catch(() => load())
    .then(
      (module) => {
        loaded[lang] = module.default;
        return module.default;
      },
      (error: unknown) => {
        delete pending[lang];
        throw error;
      },
    );
  pending[lang] = promise;
  return promise;
}
