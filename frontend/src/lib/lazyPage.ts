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
 * Страница, которая скачивается только при первом заходе на неё (FRONTEND-050).
 * После выкладки новой версии старые части удаляются: если у человека открыта старая
 * версия и часть не загрузилась, страница один раз перезагружается и получает новую.
 */
export function lazyPage<P extends object>(load: () => Promise<{ default: ComponentType<P> }>) {
  return lazy(() =>
    load().then(
      (module) => {
        writeFlag(false);
        return module;
      },
      (error: unknown) => {
        // Без sessionStorage перезагрузка могла бы повторяться — тогда просто показываем ошибку
        if (!readFlag() && writeFlag(true)) {
          window.location.reload();
          // Ждём перезагрузки, ошибку не показываем
          return new Promise<never>(() => {});
        }
        throw error;
      },
    ),
  );
}
