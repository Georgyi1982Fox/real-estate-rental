import { lazy } from 'react';
import type { ComponentType } from 'react';

// Отметка «уже перезагружали»: если и после перезагрузки часть не пришла, не зацикливаемся
const RELOAD_KEY = 'bina:chunk_reload';

function readFlag(): boolean {
  try {
    return sessionStorage.getItem(RELOAD_KEY) !== null;
  } catch {
    return false;
  }
}

function writeFlag(on: boolean): boolean {
  try {
    if (on) sessionStorage.setItem(RELOAD_KEY, '1');
    else sessionStorage.removeItem(RELOAD_KEY);
    return true;
  } catch {
    return false;
  }
}

/**
 * Части сайта не загрузились (например, после выкладки новой версии старые удалены):
 * один раз перезагружаем страницу. Возвращает false, если уже перезагружали (или без
 * sessionStorage) — тогда перезагрузки не будет, чтобы не зациклиться.
 */
export function reloadOnce(): boolean {
  if (readFlag() || !writeFlag(true)) return false;
  window.location.reload();
  return true;
}

/** Часть загрузилась — отметку о перезагрузке можно снять */
export function chunkLoaded(): void {
  writeFlag(false);
}

/**
 * Страница, которая скачивается только при первом заходе на неё (FRONTEND-050).
 * Если у человека открыта старая версия и часть не загрузилась, страница один раз
 * перезагружается и получает новую.
 */
export function lazyPage<P extends object>(load: () => Promise<{ default: ComponentType<P> }>) {
  return lazy(() =>
    load().then(
      (module) => {
        chunkLoaded();
        return module;
      },
      (error: unknown) => {
        // Ждём перезагрузки, ошибку не показываем
        if (reloadOnce()) return new Promise<never>(() => {});
        throw error;
      },
    ),
  );
}
