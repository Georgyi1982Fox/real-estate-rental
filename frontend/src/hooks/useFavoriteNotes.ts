import { useCallback, useSyncExternalStore } from 'react';
import { ApiError, apiGet, apiPut } from '../api/client';
import type { ListingId } from '../api/types';
import { usesServerFavorites } from '../lib/session';

// Заметки к избранному (FRONTEND-043): «звонил, перезвонить в пятницу». Живут только на
// сервере рядом с избранным, видит их только сам человек. Гость в браузере (избранное на
// устройстве) заметок не пишет — поле ему не показываем.

/** Предел длины заметки — как на бэкенде */
export const NOTE_MAX_LENGTH = 300;

interface NotesResponse {
  notes: Record<string, string>;
}

/** Чем закончилось сохранение: gone — квартиры уже нет в избранном (404) */
export type NoteSaveResult = 'saved' | 'gone' | 'failed';

const EMPTY: Record<string, string> = {};

// Общее состояние для всех компонентов: ID квартиры → непустая заметка
let notes = EMPTY;
let loaded: Promise<void> | null = null;
const listeners = new Set<() => void>();

function set(next: Record<string, string>): void {
  notes = next;
  listeners.forEach((listener) => listener());
}

function withNote(id: string, text: string): Record<string, string> {
  const next = { ...notes };
  if (text) next[id] = text;
  else delete next[id];
  return next;
}

/** Загрузить заметки с сервера (один раз; повторно — после входа, см. refreshFavorites) */
export function refreshNotes(): Promise<void> {
  if (!usesServerFavorites()) return Promise.resolve();
  loaded = apiGet<NotesResponse>('/api/favorites/notes').then(
    (response) => set(response.notes),
    () => {
      // Сервер недоступен — без заметок; попробуем при следующем открытии
      loaded = null;
    },
  );
  return loaded;
}

/** Квартиру убрали из избранного — сервер удалил и заметку */
export function dropNote(id: string): void {
  if (id in notes) set(withNote(id, ''));
}

/** Выход из аккаунта: заметки чужого устройства не показываем */
export function clearNotes(): void {
  loaded = null;
  set(EMPTY);
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  if (loaded === null) void refreshNotes();
  return () => listeners.delete(listener);
}

function getSnapshot(): Record<string, string> {
  return notes;
}

/** Заметки к избранному: текст по ID и сохранение (пустая строка — удалить) */
export function useFavoriteNotes() {
  const current = useSyncExternalStore(subscribe, getSnapshot);

  const noteOf = useCallback((id: ListingId) => current[String(id)] ?? '', [current]);

  const save = useCallback(async (id: ListingId, text: string): Promise<NoteSaveResult> => {
    const key = String(id);
    try {
      const saved = await apiPut<{ note: string }>(
        `/api/favorites/${encodeURIComponent(key)}/note`,
        { note: text.trim() },
      );
      // Бэкенд чистит текст от HTML — показываем то, что он сохранил
      set(withNote(key, saved.note));
      return 'saved';
    } catch (error) {
      return error instanceof ApiError && error.isNotFound ? 'gone' : 'failed';
    }
  }, []);

  return { enabled: usesServerFavorites(), noteOf, save };
}
