// FRONTEND-057: всё в интерфейсе — на выбранном языке, без смешения.
// TypeScript проверяет только одинаковые ключи главного словаря; этот тест проверяет буквы
// (в ka нет кириллицы, в ru — грузинских букв, в en — ни тех ни других) и подстановки {…}.

import { describe, expect, it } from 'vitest';
import { CONDITIONS } from './conditions';
import en from './en';
import { FEATURES } from './features';
import { AMENITIES, KINDS, ROOM_KINDS } from './hotels';
import ka from './ka';
import ru from './ru';
import type { Lang } from './strings';

/**
 * Названия, которые пишутся латиницей на любом языке. Строка из одних таких названий
 * (например, «Premium») — не ошибка; в остальном тексте они тоже не считаются.
 */
const NAMES = [
  'bina.ai',
  'Bina',
  'Premium',
  'SS.ge',
  'Google Maps',
  'Yandex Maps',
  'Wi-Fi',
  'Email',
];

/** Ключи, которые проверять не нужно: буква «Y» — значок Яндекс Карт, а не текст */
const SKIP_KEYS = ['listing.map.yandex_letter'];

const GEORGIAN = /[Ⴀ-ჿᲐ-Ჿⴀ-⴯]/;
const CYRILLIC = /[Ѐ-ӿ]/;
const LATIN = /[A-Za-z]/;
const PLACEHOLDER = /\{(\w+)\}/g;

type Dictionary = Record<Lang, unknown>;

/** Словари для проверки: главный и маленькие (удобства, состояния, гостиницы) */
const DICTIONARIES: Record<string, Dictionary> = {
  'ka.ts / ru.ts / en.ts': { ka, ru, en },
  'features.ts': FEATURES,
  'conditions.ts': CONDITIONS,
  'hotels.ts — типы объектов': KINDS,
  'hotels.ts — типы номеров': ROOM_KINDS,
  'hotels.ts — удобства': AMENITIES,
};

/** Все строки словаря: 'home.page_of' → 'Page {n} of {total}' */
function strings(value: unknown, path = '', out = new Map<string, string>()): Map<string, string> {
  if (typeof value === 'string') {
    out.set(path, value);
  } else if (value && typeof value === 'object') {
    for (const [key, item] of Object.entries(value)) {
      strings(item, path ? `${path}.${key}` : key, out);
    }
  }
  return out;
}

/** Текст без подстановок и названий из NAMES — то, что должно быть на языке словаря */
function ownText(text: string): string {
  return NAMES.reduce((rest, name) => rest.split(name).join(' '), text.replace(PLACEHOLDER, ' '));
}

/** Что не так с буквами строки; null — всё в порядке */
function letterProblem(text: string, lang: Lang): string | null {
  const own = ownText(text);
  if (lang === 'ka') {
    if (CYRILLIC.test(own)) return 'кириллица в грузинском словаре';
    if (LATIN.test(own) && !GEORGIAN.test(own)) return 'латиница без грузинских букв';
  }
  if (lang === 'ru') {
    if (GEORGIAN.test(own)) return 'грузинские буквы в русском словаре';
    if (LATIN.test(own) && !CYRILLIC.test(own)) return 'латиница без русских букв';
  }
  if (lang === 'en') {
    if (CYRILLIC.test(own)) return 'кириллица в английском словаре';
    if (GEORGIAN.test(own)) return 'грузинские буквы в английском словаре';
  }
  return null;
}

/** Подстановки строки по алфавиту: '{total} / {n}' → 'n, total' */
function placeholders(text: string): string {
  return [...new Set([...text.matchAll(PLACEHOLDER)].map((match) => match[1]))].sort().join(', ');
}

const LANGS: Lang[] = ['ka', 'ru', 'en'];

describe.each(Object.entries(DICTIONARIES))('словарь %s', (_name, dictionary) => {
  const byLang = Object.fromEntries(
    LANGS.map((lang) => [lang, strings(dictionary[lang])]),
  ) as Record<Lang, Map<string, string>>;

  it('во всех языках одни и те же ключи', () => {
    const all = [...new Set(LANGS.flatMap((lang) => [...byLang[lang].keys()]))];
    const missing = LANGS.flatMap((lang) =>
      all.filter((key) => !byLang[lang].has(key)).map((key) => `${lang}: нет ключа ${key}`),
    );
    expect(missing).toEqual([]);
  });

  it.each(LANGS)('%s: строки только на своём языке', (lang) => {
    const problems = [...byLang[lang]]
      .filter(([key]) => !SKIP_KEYS.includes(key))
      .flatMap(([key, text]) => {
        const problem = letterProblem(text, lang);
        return problem ? [`${lang} · ${key}: ${JSON.stringify(text)} — ${problem}`] : [];
      });
    expect(problems).toEqual([]);
  });

  it('одинаковые подстановки {…} во всех языках', () => {
    const problems = [...byLang.ka].flatMap(([key, text]) => {
      const expected = placeholders(text);
      return LANGS.slice(1).flatMap((lang) => {
        const other = byLang[lang].get(key);
        if (other === undefined) return [];
        const actual = placeholders(other);
        return actual === expected
          ? []
          : [`${key}: ka {${expected}}, ${lang} {${actual}} — ${JSON.stringify(other)}`];
      });
    });
    expect(problems).toEqual([]);
  });
});

// Сама проверка тоже проверяется: если она сломается, тесты выше молча пройдут
describe('проверка букв', () => {
  it('находит русское слово в грузинском словаре', () => {
    expect(letterProblem('Тест', 'ka')).not.toBeNull();
    expect(letterProblem('ძებნა Тест', 'ka')).not.toBeNull();
  });

  it('находит грузинское слово в русском и английском словарях', () => {
    expect(letterProblem('Поиск ძებნა', 'ru')).not.toBeNull();
    expect(letterProblem('Search ძებნა', 'en')).not.toBeNull();
    expect(letterProblem('Поиск', 'en')).not.toBeNull();
  });

  it('находит непереведённый английский текст', () => {
    expect(letterProblem('Search', 'ka')).not.toBeNull();
    expect(letterProblem('Search', 'ru')).not.toBeNull();
  });

  it('пропускает названия и подстановки', () => {
    expect(letterProblem('Premium', 'ka')).toBeNull();
    expect(letterProblem('{price} ⭐ / {days}', 'ru')).toBeNull();
    expect(letterProblem('რა შეუძლია bina.ai-ს', 'ka')).toBeNull();
  });

  it('сравнивает подстановки без учёта порядка', () => {
    expect(placeholders('Страница {n} из {total}')).toBe(placeholders('{total}: {n}'));
    expect(placeholders('Page {n} of')).not.toBe(placeholders('Страница {n} из {total}'));
  });
});
