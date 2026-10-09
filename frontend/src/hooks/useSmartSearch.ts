import { useSyncExternalStore } from 'react';

// «По смыслу» включён, пока человек сам его не выключил; выбор один на всё приложение
// и хранится в localStorage: '0' — выключен, нет записи — включён.
const STORAGE_KEY = 'bina:smart_search';
const OFF = '0';

function load(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) !== OFF;
  } catch {
    // localStorage может быть недоступен (приватный режим) — работаем только в памяти
    return true;
  }
}

let enabled = load();
const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((listener) => listener());
}

/** Изменение в другой вкладке (key === null — хранилище очищено целиком) */
function handleStorage(event: StorageEvent): void {
  if (event.key !== null && event.key !== STORAGE_KEY) return;
  enabled = load();
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

function getSnapshot(): boolean {
  return enabled;
}

/** Запомнить выбор; сразу обновляет все компоненты */
export function saveSmartSearch(next: boolean): void {
  if (next === enabled) return;
  enabled = next;
  try {
    if (next) window.localStorage.removeItem(STORAGE_KEY);
    else window.localStorage.setItem(STORAGE_KEY, OFF);
  } catch {
    // Не удалось сохранить — останется до перезагрузки страницы
  }
  emit();
}

/** Запомненный выбор «По смыслу» (FRONTEND-031): true, пока человек его не выключил */
export function useSmartSearch(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot);
}
