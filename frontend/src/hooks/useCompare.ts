import { useCallback, useSyncExternalStore } from 'react';
import type { ListingId } from '../api/types';
import { COMPARE_MAX } from '../lib/compare';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

// Квартиры, отмеченные для сравнения (FRONTEND-027): до 3 ID, только на этом устройстве.
// Порядок — порядок выбора: так же идут колонки на экране сравнения
const STORAGE_KEY = 'bina:compare';
const EMPTY: string[] = [];

/** Повреждённое значение — пустой выбор; лишнее сверх максимума отбрасываем */
function parse(raw: string | null): string[] {
  if (!raw) return EMPTY;
  try {
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value)) return EMPTY;
    const ids = value.filter((item): item is string => typeof item === 'string' && item !== '');
    return [...new Set(ids)].slice(0, COMPARE_MAX);
  } catch {
    return EMPTY;
  }
}

function load(): string[] {
  try {
    return parse(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    // localStorage недоступен (приватный режим) — выбор живёт только в памяти
    return EMPTY;
  }
}

let ids = load();
const listeners = new Set<() => void>();

function save(next: string[]): void {
  ids = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Не сохранилось — останется до перезагрузки
  }
  listeners.forEach((listener) => listener());
}

/** Изменение в другой вкладке (key === null — хранилище очищено целиком) */
function handleStorage(event: StorageEvent): void {
  if (event.key !== null && event.key !== STORAGE_KEY) return;
  ids = load();
  listeners.forEach((listener) => listener());
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

/** Выбор для сравнения: общий для всех компонентов, «максимум 3» — подсказкой */
export function useCompare() {
  const current = useSyncExternalStore(subscribe, getSnapshot);
  const { t } = useI18n();
  const showToast = useToast();

  const has = useCallback((id: ListingId) => current.includes(String(id)), [current]);

  const remove = useCallback((id: ListingId) => {
    const key = String(id);
    if (!ids.includes(key)) return;
    save(ids.filter((item) => item !== key));
    haptic('light');
  }, []);

  const toggle = useCallback(
    (id: ListingId) => {
      const key = String(id);
      if (ids.includes(key)) {
        remove(key);
        return;
      }
      // Четвёртая не добавляется
      if (ids.length >= COMPARE_MAX) {
        haptic('warning');
        showToast(t.compare.full, 'info');
        return;
      }
      save([...ids, key]);
      haptic('light');
    },
    [remove, showToast, t],
  );

  const clear = useCallback(() => {
    save(EMPTY);
    haptic('light');
  }, []);

  return { ids: current, count: current.length, has, toggle, remove, clear };
}
