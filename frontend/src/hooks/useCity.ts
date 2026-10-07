import { useMemo, useSyncExternalStore } from 'react';
import type { City, ListResponse, Localized } from '../api/types';
import { ALL_CITIES } from '../lib/searchFilters';
import { useApi } from './useApi';

// Выбранный город — один на всё приложение (лента, главная, фильтр районов).
// Хранится в localStorage: код города или ALL_CITIES («Вся Грузия»).
const STORAGE_KEY = 'bina:city';
export const DEFAULT_CITY = 'tbilisi';

export type CityNames = Record<string, Localized>;

function load(): string {
  try {
    return window.localStorage.getItem(STORAGE_KEY)?.trim() || DEFAULT_CITY;
  } catch {
    // localStorage может быть недоступен (приватный режим) — работаем только в памяти
    return DEFAULT_CITY;
  }
}

let choice = load();
const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((listener) => listener());
}

/** Изменение в другой вкладке (key === null — хранилище очищено целиком) */
function handleStorage(event: StorageEvent): void {
  if (event.key !== null && event.key !== STORAGE_KEY) return;
  choice = load();
  emit();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  if (listeners.size === 1) window.addEventListener('storage', handleStorage);
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) window.removeEventListener('storage', handleStorage);
  };
}

function getSnapshot(): string {
  return choice;
}

/** Код города из адреса или хранилища → параметр city для API; «Вся Грузия» — без city */
export function cityParam(code: string): string | undefined {
  return code === ALL_CITIES ? undefined : code;
}

/** Запомнить город; undefined — «Вся Грузия». Сразу обновляет все компоненты */
export function saveCity(city: string | undefined): void {
  const next = city ?? ALL_CITIES;
  if (next === choice) return;
  choice = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // Не удалось сохранить — останется до перезагрузки страницы
  }
  emit();
}

/**
 * Выбранный город и список городов из GET /api/cities.
 * city — код для параметра city; undefined — «Вся Грузия».
 */
export function useCity() {
  const stored = useSyncExternalStore(subscribe, getSnapshot);
  const { data, error, loading, reload } = useApi<ListResponse<City>>('/api/cities', {
    remember: true,
  });
  const cities = useMemo(() => data?.items ?? [], [data]);
  const names = useMemo<CityNames>(
    () => Object.fromEntries(cities.map((city) => [city.code, city.name])),
    [cities],
  );

  // В списке только города с объявлениями: запомненного города там может уже не быть
  let code = stored;
  if (data && stored !== ALL_CITIES && !names[stored]) {
    code = names[DEFAULT_CITY] ? DEFAULT_CITY : ALL_CITIES;
  }

  return { city: cityParam(code), cities, names, loading, error, reload, setCity: saveCity };
}
