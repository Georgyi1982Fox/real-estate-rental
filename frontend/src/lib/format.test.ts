import { describe, expect, it } from 'vitest';
import {
  fill,
  fillVars,
  formatDate,
  formatMoney,
  formatNumber,
  formatPrice,
  listingTime,
  plural,
  timeAgo,
  tr,
} from './format';

/** Местное время (как у человека в браузере): месяцы с 1, а не с 0 */
function at(year: number, month: number, day: number, hour = 12, minute = 0): Date {
  return new Date(year, month - 1, day, hour, minute);
}

const NOW = at(2026, 11, 27, 15, 30);
const ago = (date: Date) => date.toISOString();

describe('цены', () => {
  it('разделяет тысячи пробелом и ставит знак валюты', () => {
    expect(formatPrice(1200)).toBe('1 200 ₾');
    expect(formatPrice(1234567, 'USD')).toBe('1 234 567 $');
    expect(formatPrice(99.6, 'EUR')).toBe('100 €');
    expect(formatPrice(-1500)).toBe('-1 500 ₾');
  });

  it('незнакомая валюта — кодом, мусор — ноль', () => {
    expect(formatPrice(500, 'TRY')).toBe('500 TRY');
    expect(formatPrice('abc')).toBe('0 ₾');
    expect(formatPrice(null)).toBe('0 ₾');
  });

  it('копейки — только если они есть', () => {
    expect(formatMoney(1200)).toBe('1 200 ₾');
    expect(formatMoney(12.5)).toBe('12.50 ₾');
    expect(formatMoney(0)).toBe('0 ₾');
  });

  it('дробное число с разделителем языка', () => {
    expect(formatNumber(2.7, 'ka')).toBe('2,7');
    expect(formatNumber(2.7, 'ru')).toBe('2,7');
    expect(formatNumber(2.7, 'en')).toBe('2.7');
  });
});

describe('даты', () => {
  it('грузинские месяцы — свои, а не английские', () => {
    expect(formatDate(ago(at(2026, 9, 27)), 'ka')).toBe('27 სექტემბერი, 2026');
    expect(formatDate(ago(at(2026, 9, 27)), 'ru')).toMatch(/^27 сентября 2026/);
    expect(formatDate(ago(at(2026, 9, 27)), 'en')).toBe('27 September 2026');
    expect(formatDate('не дата', 'ru')).toBe('');
  });

  it('«сейчас»', () => {
    const justNow = ago(new Date(NOW.getTime() - 20_000));
    expect(timeAgo(justNow, 'ka', NOW)).toBe('ახლა');
    expect(timeAgo(ago(NOW), 'ru', NOW)).toBe('сейчас');
    expect(timeAgo(ago(NOW), 'en', NOW)).toBe('now');
  });

  it('сегодня: минуты и часы назад', () => {
    const minutes = ago(at(2026, 11, 27, 15, 25));
    expect(timeAgo(minutes, 'ka', NOW)).toBe('5 წთ წინ');
    expect(timeAgo(minutes, 'ru', NOW)).toMatch(/^5 мин.* назад$/);
    expect(timeAgo(minutes, 'en', NOW)).toMatch(/^5 min.* ago$/);

    const hours = ago(at(2026, 11, 27, 12, 30));
    expect(timeAgo(hours, 'ka', NOW)).toBe('3 სთ წინ');
    expect(timeAgo(hours, 'ru', NOW)).toMatch(/^3 ч.* назад$/);
    expect(timeAgo(hours, 'en', NOW)).toMatch(/^3 h.* ago$/);
  });

  it('«вчера» — по календарю, а не 24 часа', () => {
    const lateYesterday = ago(at(2026, 11, 26, 22, 0));
    expect(timeAgo(lateYesterday, 'ka', at(2026, 11, 27, 8, 0))).toBe('გუშინ');
    expect(timeAgo(lateYesterday, 'ru', at(2026, 11, 27, 8, 0))).toBe('вчера');
    expect(timeAgo(lateYesterday, 'en', at(2026, 11, 27, 8, 0))).toBe('yesterday');
  });

  it('N дней назад, старше недели — дата', () => {
    const days = ago(at(2026, 11, 23));
    expect(timeAgo(days, 'ka', NOW)).toBe('4 დღის წინ');
    expect(timeAgo(days, 'ru', NOW)).toMatch(/^4 д.* назад$/);
    expect(timeAgo(days, 'en', NOW)).toBe('4 days ago');
    expect(timeAgo(ago(at(2026, 11, 2)), 'ka', NOW)).toBe('2 ნოემბერი, 2026');
  });

  it('будущее время (часы сервера спешат) — «сейчас»', () => {
    expect(timeAgo(ago(at(2026, 11, 27, 16, 0)), 'en', NOW)).toBe('now');
  });

  it('время объявления: сегодня — «чч:мм назад», в этом году — без года', () => {
    expect(listingTime(ago(at(2026, 11, 27, 14, 5)), 'ru', '{n} ч назад', NOW)).toBe('01:25 ч назад');
    expect(listingTime(ago(at(2026, 8, 31)), 'en', '{n}', NOW)).toBe('31 August');
    expect(listingTime(ago(at(2025, 8, 31)), 'en', '{n}', NOW)).toBe('31 August 2025');
  });
});

describe('подстановки и формы слов', () => {
  it('fill и fillVars', () => {
    expect(fill('Страница {n}', 3)).toBe('Страница 3');
    expect(fillVars('Page {n} of {total}', { n: 2, total: 9 })).toBe('Page 2 of 9');
    expect(fillVars('{old} → {price}', { old: '1 ₾' })).toBe('1 ₾ → {price}');
  });

  it('формы слова по правилам языка', () => {
    const forms = { one: '{n} квартира', few: '{n} квартиры', many: '{n} квартир', other: '{n} квартиры' };
    expect(plural(forms, 1, 'ru')).toBe('1 квартира');
    expect(plural(forms, 3, 'ru')).toBe('3 квартиры');
    expect(plural(forms, 5, 'ru')).toBe('5 квартир');
    const enForms = { one: '{n} flat', few: '', many: '', other: '{n} flats' };
    expect(plural(enForms, 1, 'en')).toBe('1 flat');
    expect(plural(enForms, 2, 'en')).toBe('2 flats');
  });

  it('значение на нужном языке, без него — ka → en → ru', () => {
    const name = { ka: 'ვაკე', ru: 'Ваке', en: 'Vake' };
    expect(tr(name, 'ru')).toBe('Ваке');
    expect(tr({ ru: 'Ваке', en: 'Vake' }, 'ka')).toBe('Vake');
    expect(tr('как есть', 'en')).toBe('как есть');
    expect(tr(null, 'ka')).toBe('');
  });
});
