import { useCallback, useEffect, useState } from 'react';
import { ApiError, apiGet } from '../api/client';
import type { Listing, ListingsPage } from '../api/types';
import { listingPreview } from '../lib/listingPreview';
import { usesServerFavorites } from '../lib/session';
import { useFavoritesServerVersion } from './useFavorites';

// Избранное НЕ грузится через GET /api/listings/{id}: этот запрос — «открыли объявление»
// (+1 «👁» и запись в «Недавно смотрели»). Вместо него — список GET /api/favorites.
const PER_PAGE = 50;
const GUEST_CARDS_KEY = 'bina:favorite_cards';

// Последний ответ /api/favorites — на время сессии: повторный заход на страницу мгновенный
let serverCards = new Map<string, Listing>();
let serverLoaded = false;

/** Всё избранное с сервера, страница за страницей (новые сверху) */
async function fetchAllFavorites(signal: AbortSignal): Promise<Listing[]> {
  const url = (page: number) => `/api/favorites?page=${page}&per_page=${PER_PAGE}`;
  const first = await apiGet<ListingsPage>(url(1), signal);
  const rest = await Promise.all(
    Array.from({ length: Math.max(0, first.pages - 1) }, (_, index) =>
      apiGet<ListingsPage>(url(index + 2), signal),
    ),
  );
  return [first, ...rest].flatMap((page) => page.items);
}

// Гость в браузере: сервера избранного у него нет, карточки хранятся на устройстве
function loadGuestCards(): Record<string, Listing> {
  try {
    const value: unknown = JSON.parse(window.localStorage.getItem(GUEST_CARDS_KEY) ?? '{}');
    return value && typeof value === 'object' && !Array.isArray(value)
      ? (value as Record<string, Listing>)
      : {};
  } catch {
    return {};
  }
}

let guestCards = loadGuestCards();

/** Запомнить карточки избранного гостя; убранные из избранного — забыть */
function storeGuestCards(ids: string[]): void {
  const next: Record<string, Listing> = {};
  for (const id of ids) {
    const card = listingPreview(id) ?? guestCards[id];
    if (card) next[id] = card;
  }
  guestCards = next;
  try {
    window.localStorage.setItem(GUEST_CARDS_KEY, JSON.stringify(next));
  } catch {
    // Не удалось сохранить — карточки останутся до перезагрузки страницы
  }
}

export interface FavoriteListings {
  /** Квартиры в порядке ids; удалённых с сайта сервер не возвращает — их не видно */
  listings: Listing[];
  loading: boolean;
  error: ApiError | undefined;
  reload: () => void;
}

/**
 * Квартиры избранного в порядке ids. Добавление и удаление ♥ видны сразу: список
 * фильтруется по ids, а для только что добавленной квартиры берутся данные её карточки.
 */
export function useFavoriteListings(ids: string[]): FavoriteListings {
  const server = usesServerFavorites();
  const serverVersion = useFavoritesServerVersion();
  const [, setVersion] = useState(0);
  const [error, setError] = useState<ApiError>();
  const [loading, setLoading] = useState(server && !serverLoaded);
  const [attempt, setAttempt] = useState(0);

  // Заново — после каждого подтверждённого сервером изменения ♥ (один запрос, без «👁»)
  useEffect(() => {
    if (!server) return;
    const controller = new AbortController();
    setError(undefined);
    if (!serverLoaded) setLoading(true);
    fetchAllFavorites(controller.signal).then(
      (items) => {
        serverCards = new Map(items.map((listing) => [String(listing.id), listing]));
        serverLoaded = true;
        setLoading(false);
        setVersion((version) => version + 1);
      },
      (err: unknown) => {
        if (controller.signal.aborted) return;
        setLoading(false);
        // Уже показанный список не прячем за ошибкой — обновится при следующем изменении
        if (!serverLoaded) setError(err instanceof ApiError ? err : new ApiError(0, String(err)));
      },
    );
    return () => controller.abort();
  }, [server, serverVersion, attempt]);

  const idsKey = ids.join(',');
  useEffect(() => {
    if (!server) storeGuestCards(idsKey ? idsKey.split(',') : []);
  }, [server, idsKey]);

  const reload = useCallback(() => setAttempt((value) => value + 1), []);

  const listings = ids
    .map((id) => (server ? serverCards.get(id) : guestCards[id]) ?? listingPreview(id))
    .filter((listing): listing is Listing => listing !== undefined);
  return { listings, loading, error, reload };
}
