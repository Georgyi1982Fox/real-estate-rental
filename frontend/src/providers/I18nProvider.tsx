import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { LANGUAGES, STRINGS } from '../i18n/strings';
import type { Lang, Strings } from '../i18n/strings';

const STORAGE_KEY = 'bina_lang';
const DEFAULT_LANG: Lang = 'ka';

function isLang(value: unknown): value is Lang {
  return LANGUAGES.some((item) => item.code === value);
}

// Язык: ?lang= → сохранённый выбор → ქართული (по умолчанию)
function resolveInitialLang(): Lang {
  const queryLang = new URLSearchParams(window.location.search).get('lang');
  if (isLang(queryLang)) return queryLang;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (isLang(stored)) return stored;
  } catch {
    // localStorage может быть недоступен (приватный режим) — не критично
  }
  return DEFAULT_LANG;
}

interface I18nContextValue {
  lang: Lang;
  t: Strings;
  setLang: (lang: Lang) => void;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(resolveInitialLang);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // см. выше
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const value = useMemo(() => ({ lang, t: STRINGS[lang], setLang }), [lang, setLang]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) throw new Error('useI18n must be used inside <I18nProvider>');
  return context;
}
