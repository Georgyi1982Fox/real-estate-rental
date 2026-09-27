import { useCallback, useSyncExternalStore } from 'react';
import type { ListingId } from '../api/types';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

// Единственное место работы с хранилищем избранного.
// При переходе на /api/favorites меняется только этот файл — компоненты работают через useFavorites().
const STORAGE_KEY = 'bina:favorites';
const EMPTY: string[] = [];

/** Повреждённое или пустое значение считаем пустым списком; ID — только непустые строки */
function parse(raw: string | null): string[] {
  if (!raw) return EMPTY;
  try {
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value)) return EMPTY;
    const ids = value.filter((item): item is string => typeof item === 'string' && item !== '');
    return [...new Set(ids)];
  } catch {
    return EMPTY;
  }
}

function load(): string[] {
  try {
    return parse(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    // localStorage может быть недоступен (приватный режим) — работаем только в памяти
    return EMPTY;
  }
}

// Общее состояние для всех компонентов: снимок в памяти + подписчики useSyncExternalStore
let ids = load();
const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((listener) => listener());
}

function save(next: string[]): void {
  ids = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Не удалось сохранить — избранное останется до перезагрузки страницы
  }
  emit();
}

/** Изменение в другой вкладке (key === null — хранилище очищено целиком) */
function handleStorage(event: StorageEvent): void {
  if (event.key !== null && event.key !== STORAGE_KEY) return;
  ids = load();
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

function getSnapshot(): string[] {
  return ids;
}

/** Очистить избранное (выход из аккаунта) — сразу обновляет все компоненты */
export function clearFavorites(): void {
  ids = EMPTY;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // см. load()
  }
  emit();
}

/** Избранные квартиры: общий список ID (строки) с toast и haptic при изменении */
export function useFavorites() {
  const current = useSyncExternalStore(subscribe, getSnapshot);
  const { t } = useI18n();
  const showToast = useToast();

  const isFavorite = useCallback((id: ListingId) => current.includes(String(id)), [current]);

  const add = useCallback(
    (id: ListingId) => {
      const key = String(id);
      if (ids.includes(key)) return;
      save([...ids, key]);
      showToast(t.card.added, 'success');
      haptic('light');
    },
    [showToast, t],
  );

  const remove = useCallback(
    (id: ListingId) => {
      const key = String(id);
      if (!ids.includes(key)) return;
      save(ids.filter((item) => item !== key));
      showToast(t.card.removed, 'success');
      haptic('light');
    },
    [showToast, t],
  );

  const toggle = useCallback(
    (id: ListingId) => (ids.includes(String(id)) ? remove(id) : add(id)),
    [add, remove],
  );

  return { ids: current, count: current.length, isFavorite, add, remove, toggle };
}
