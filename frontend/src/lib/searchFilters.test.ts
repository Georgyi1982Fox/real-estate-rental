import { describe, expect, it } from 'vitest';
import type { SearchFilters } from '../api/types';
import {
  countFilters,
  filtersToQuery,
  fromSavedFilters,
  parseFilters,
  parseSort,
  sameFilters,
  toSavedFilters,
} from './searchFilters';

/** Фильтры → адрес страницы → фильтры */
function roundTrip(filters: SearchFilters): SearchFilters {
  return parseFilters(new URLSearchParams(filtersToQuery(filters)));
}

const FULL: SearchFilters = {
  districts: ['saburtalo', 'vake'],
  min_price: 500,
  max_price: 1500,
  rooms: 2,
  min_area: 40,
  max_area: 90,
  floor_min: 2,
  floor_max: 10,
  bedrooms: 1,
  bathrooms: 1,
  not_first_floor: true,
  not_last_floor: true,
  owner_only: true,
  price_dropped: true,
  features: ['balcony', 'parking'],
  condition: ['renovated'],
  source: ['ss', 'myhome'],
  city: 'batumi,tbilisi',
  rent_period: 'daily',
};

describe('фильтры в адресе страницы', () => {
  it('туда и обратно — те же фильтры', () => {
    expect(roundTrip(FULL)).toEqual(FULL);
    expect(roundTrip({})).toEqual({});
    expect(roundTrip({ rooms: 3 })).toEqual({ rooms: 3 });
  });

  it('адрес читается глазами: запятые не кодируются, порядок постоянный', () => {
    expect(filtersToQuery({ rooms: 2, districts: ['vake', 'saburtalo'] })).toBe(
      'district=saburtalo,vake&rooms=2',
    );
    expect(sameFilters({ districts: ['a', 'b'] }, { districts: ['b', 'a'] })).toBe(true);
  });

  it('неизвестные параметры отбрасываются', () => {
    const params = new URLSearchParams('rooms=2&foo=bar&utm_source=tg&page=3&q=ваке');
    expect(parseFilters(params)).toEqual({ rooms: 2 });
  });

  it('мусорные значения отбрасываются', () => {
    const params = new URLSearchParams(
      'rooms=9&min_price=-5&max_price=abc&floor_min=0&owner_only=yes&source=ss,unknown&rent_period=weekly',
    );
    expect(parseFilters(params)).toEqual({ source: ['ss'] });
  });

  it('флаги — и true, и 1; monthly в адресе не держим', () => {
    expect(parseFilters(new URLSearchParams('price_dropped=1&owner_only=true'))).toEqual({
      price_dropped: true,
      owner_only: true,
    });
    expect(filtersToQuery({ rent_period: 'monthly' })).toBe('');
  });

  it('районы — и через запятую, и повтором параметра, без повторов', () => {
    const params = new URLSearchParams('district=vake,saburtalo&district=vake');
    expect(parseFilters(params)).toEqual({ districts: ['vake', 'saburtalo'] });
  });

  it('сортировка: знакомая — да, незнакомая и smart — нет', () => {
    expect(parseSort('price_asc')).toBe('price_asc');
    expect(parseSort('smart')).toBeUndefined();
    expect(parseSort('cheap')).toBeUndefined();
  });
});

describe('счётчик и сохранённые поиски', () => {
  it('цена, площадь и этаж считаются за один фильтр; город и срок — не фильтры', () => {
    expect(
      countFilters({
        min_price: 1,
        max_price: 2,
        floor_min: 2,
        not_last_floor: true,
        city: 'tbilisi',
        rent_period: 'daily',
      }),
    ).toBe(2);
  });

  it('в сохранённый поиск не попадает «Только подешевевшие»', () => {
    expect(toSavedFilters({ rooms: 2, price_dropped: true })).toEqual({ rooms: 2 });
  });

  it('один район и город — старые поля, несколько — списки, и обратно', () => {
    expect(toSavedFilters({ districts: ['vake'], city: 'tbilisi' })).toEqual({
      district: 'vake',
      city: 'tbilisi',
    });
    const saved = toSavedFilters({ districts: ['vake', 'saburtalo'], city: 'tbilisi,batumi' });
    expect(saved).toEqual({ districts: ['vake', 'saburtalo'], cities: ['tbilisi', 'batumi'] });
    expect(fromSavedFilters(saved)).toEqual({
      districts: ['vake', 'saburtalo'],
      city: 'batumi,tbilisi',
    });
  });
});
