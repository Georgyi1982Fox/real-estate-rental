// «Мои данные» в профиле: скачать всё, что хранится о пользователе, и удалить аккаунт
// (бэкенд — TASK-059 / TASK-060)

import { apiDelete, apiGet } from '../api/client';
import { forgetResponses } from '../hooks/useApi';
import { clearFavorites } from '../hooks/useFavorites';

export const EXPORT_FILE_NAME = 'bina-my-data.json';

/** Ключи localStorage этого приложения; язык интерфейса (bina_lang) не трогаем */
const STORAGE_PREFIX = 'bina:';

/**
 * GET /api/me/export и сохранение ответа файлом bina-my-data.json.
 * Внутри Telegram скачивание работает не во всех клиентах, а узнать, сохранился ли файл,
 * нельзя — поэтому там под кнопкой показываем подсказку про бота
 */
export async function downloadMyData(): Promise<void> {
  const data = await apiGet<unknown>('/api/me/export');
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = EXPORT_FILE_NAME;
  link.rel = 'noopener';
  document.body.append(link);
  link.click();
  link.remove();
  // Браузеру нужно время, чтобы начать скачивание, прежде чем ссылка исчезнет
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** DELETE /api/me?confirm=true (204) и очистка всего, что приложение хранит на устройстве */
export async function deleteAccount(): Promise<void> {
  await apiDelete('/api/me?confirm=true');
  clearLocalData();
}

/** Избранное гостя, заметки, сравнение, черновики, кэш ответов — всё, кроме языка */
function clearLocalData(): void {
  clearFavorites();
  forgetResponses('');
  try {
    const storage = window.localStorage;
    const keys = Array.from({ length: storage.length }, (_, index) => storage.key(index));
    for (const key of keys) {
      if (key?.startsWith(STORAGE_PREFIX)) storage.removeItem(key);
    }
  } catch {
    // localStorage может быть недоступен (приватный режим)
  }
}
