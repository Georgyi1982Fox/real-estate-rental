import { useCallback, useSyncExternalStore } from 'react';
import { ApiError, apiDelete, apiGet, apiPost } from '../api/client';
import type { ListingId } from '../api/types';
import { isSignedOut } from '../lib/session';
import { getInitData, haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import { showPremiumPrompt } from './usePremiumPrompt';

// Единственное место работы с избранным; компоненты работают через useFavorites().
//
// В Telegram избранное хранится на сервере (/api/favorites): не пропадает при закрытии
// Mini App и одинаково на всех устройствах. localStorage — только быстрый кэш для первого
// показа. Гость в браузере (без initData) хранит избранное только в localStorage.
const STORAGE_KEY = 'bina:favorites';
const EMPTY: string[] = [];

interface FavoriteIdsResponse {
  ids: string[];
}

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

/** Пользователь Telegram, который не нажал «Выйти»: избранное живёт на сервере */
function usesServer(): boolean {
  return getInitData() !== '' && !isSignedOut();
}

// Общее состояние для всех компонентов: снимок в памяти + подписчики useSyncExternalStore.
// Порядок: старые → новые (последний добавленный — в конце)
let ids = load();
let synced: Promise<void> | null = null;
const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((listener) => listener());
}

function save(next: string[]): void {
  ids = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Не удалось сохранить — останется до перезагрузки страницы
  }
  emit();
}

/**
 * Загрузить избранное с сервера. Избранное, накопленное локально до перехода на сервер
 * (или добавленное без сети), отправляется на сервер — ничего не теряется.
 */
async function syncWithServer(): Promise<void> {
  const local = ids;
  const { ids: serverNewestFirst } = await apiGet<FavoriteIdsResponse>('/api/favorites/ids');
  const server = [...serverNewestFirst].reverse();
  const missing = local.filter((id) => !server.includes(id));
  const uploaded: string[] = [];
  for (const id of missing) {
    try {
      await apiPost('/api/favorites', { listing_id: id });
      uploaded.push(id);
    } catch {
      // Объявление удалено (404), лимит тарифа (402) или сеть — пропускаем
    }
  }
  // Изменения, сделанные пока шла синхронизация, не теряем
  const merged = [...server, ...uploaded];
  const addedMeanwhile = ids.filter((id) => !local.includes(id) && !merged.includes(id));
  const removedMeanwhile = local.filter((id) => !ids.includes(id));
  save([...merged, ...addedMeanwhile].filter((id) => !removedMeanwhile.includes(id)));
}

/** Синхронизировать с сервером (один раз; повторно — после входа, см. AuthProvider) */
export function refreshFavorites(): Promise<void> {
  if (!usesServer()) return Promise.resolve();
  synced = syncWithServer().catch(() => {
    // Сервер недоступен — показываем кэш, попробуем при следующем открытии
    synced = null;
  });
  return synced;
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
  if (synced === null) void refreshFavorites();
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) window.removeEventListener('storage', handleStorage);
  };
}

function getSnapshot(): string[] {
  return ids;
}

/**
 * Очистить локальный кэш избранного (выход из аккаунта) — сразу обновляет все компоненты.
 * На сервере избранное остаётся и вернётся после входа.
 */
export function clearFavorites(): void {
  ids = EMPTY;
  synced = null;
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
      // Сердечко — сразу, сервер — следом; при ошибке откатываем
      save([...ids, key]);
      haptic('light');
      if (!usesServer()) {
        showToast(t.card.added, 'success');
        return;
      }
      // Toast «Добавлено» — только после ответа: на лимите тарифа вместо него будет окно Premium
      apiPost('/api/favorites', { listing_id: key }).then(
        () => showToast(t.card.added, 'success'),
        (error: unknown) => {
          save(ids.filter((item) => item !== key));
          if (error instanceof ApiError && error.isPaymentRequired) {
            haptic('warning');
            showPremiumPrompt('favorites');
            return;
          }
          showToast(t.card.favorite_error, 'error');
          haptic('error');
        },
      );
    },
    [showToast, t],
  );

  const remove = useCallback(
    (id: ListingId) => {
      const key = String(id);
      if (!ids.includes(key)) return;
      const before = ids;
      save(ids.filter((item) => item !== key));
      showToast(t.card.removed, 'success');
      haptic('light');
      if (!usesServer()) return;
      apiDelete(`/api/favorites/${encodeURIComponent(key)}`).catch(() => {
        save(before.filter((item) => item === key || ids.includes(item)));
        showToast(t.card.favorite_error, 'error');
        haptic('error');
      });
    },
    [showToast, t],
  );

  const toggle = useCallback(
    (id: ListingId) => (ids.includes(String(id)) ? remove(id) : add(id)),
    [add, remove],
  );

  return { ids: current, count: current.length, isFavorite, add, remove, toggle };
}
