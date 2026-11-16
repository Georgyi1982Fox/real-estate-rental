import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import PageSkeleton from '../components/PageSkeleton';
import {
  DEFAULT_LANG,
  DEFAULT_STRINGS,
  LANGUAGES,
  loadedStrings,
  loadStrings,
} from '../i18n/strings';
import type { Lang, Strings } from '../i18n/strings';
import { reloadOnce } from '../lib/lazyPage';

const STORAGE_KEY = 'bina_lang';

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
  /**
   * Сменить язык без перезагрузки. Пока словарь скачивается, остаётся прежний язык
   * целиком; промис — со словарём нового языка или ошибкой (тогда язык не меняется)
   */
  setLang: (lang: Lang) => Promise<Strings>;
  /** Сбросить выбор языка (выход из аккаунта): удаляет bina_lang, язык — по умолчанию */
  resetLang: () => void;
}

const I18nContext = createContext<I18nContextValue | null>(null);

function saveLang(lang: Lang | null) {
  try {
    if (lang) window.localStorage.setItem(STORAGE_KEY, lang);
    else window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // localStorage может быть недоступен (приватный режим) — не критично
  }
}

interface Shown {
  lang: Lang;
  t: Strings;
}

export function I18nProvider({ children }: { children: ReactNode }) {
  // Показываем язык только со скачанным словарём — смеси языков не бывает (FRONTEND-054).
  // null: словарь первого языка (ru / en) ещё грузится — вместо текстов заглушка
  const [shown, setShown] = useState<Shown | null>(() => {
    const initial = resolveInitialLang();
    const t = loadedStrings(initial);
    return t ? { lang: initial, t } : null;
  });
  // Последний выбранный язык: если переключили дважды подряд, побеждает последний
  const wanted = useRef<Lang>(shown?.lang ?? resolveInitialLang());

  useEffect(() => {
    if (shown) return;
    const initial = wanted.current;
    let active = true;
    loadStrings(initial).then(
      (t) => {
        if (active && wanted.current === initial) setShown({ lang: initial, t });
      },
      () => {
        // Не пришёл и после повтора: одна перезагрузка (как у страниц), потом — ქართული
        if (reloadOnce() || !active) return;
        wanted.current = DEFAULT_LANG;
        setShown({ lang: DEFAULT_LANG, t: DEFAULT_STRINGS });
      },
    );
    return () => {
      active = false;
    };
  }, [shown]);

  const setLang = useCallback((next: Lang) => {
    wanted.current = next;
    return loadStrings(next).then((t) => {
      if (wanted.current === next) {
        setShown({ lang: next, t });
        saveLang(next);
      }
      return t;
    });
  }, []);

  const resetLang = useCallback(() => {
    wanted.current = DEFAULT_LANG;
    setShown({ lang: DEFAULT_LANG, t: DEFAULT_STRINGS });
    saveLang(null);
  }, []);

  const lang = shown?.lang;
  useEffect(() => {
    if (lang) document.documentElement.lang = lang;
  }, [lang]);

  const value = useMemo(
    () => (shown ? { lang: shown.lang, t: shown.t, setLang, resetLang } : null),
    [shown, setLang, resetLang],
  );
  if (!value) {
    return (
      <div className="mx-auto w-full max-w-screen-xl px-4 pt-4 sm:px-6 lg:px-8">
        <PageSkeleton />
      </div>
    );
  }
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) throw new Error('useI18n must be used inside <I18nProvider>');
  return context;
}
