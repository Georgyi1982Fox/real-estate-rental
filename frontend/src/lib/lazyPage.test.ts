import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { chunkLoaded, reloadOnce } from './lazyPage';

/** sessionStorage в памяти — тесты идут без браузера */
function memoryStorage(): Storage {
  const items = new Map<string, string>();
  return {
    get length() {
      return items.size;
    },
    clear: () => items.clear(),
    getItem: (key) => items.get(key) ?? null,
    key: (index) => [...items.keys()][index] ?? null,
    removeItem: (key) => void items.delete(key),
    setItem: (key, value) => void items.set(key, value),
  };
}

describe('перезагрузка, если часть сайта не пришла', () => {
  const reload = vi.fn();

  beforeEach(() => {
    reload.mockClear();
    vi.stubGlobal('sessionStorage', memoryStorage());
    vi.stubGlobal('window', { location: { reload } });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('перезагружает только один раз — не зацикливается', () => {
    expect(reloadOnce()).toBe(true);
    expect(reloadOnce()).toBe(false);
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it('после удачной загрузки снова можно перезагрузить', () => {
    reloadOnce();
    chunkLoaded();
    expect(reloadOnce()).toBe(true);
    expect(reload).toHaveBeenCalledTimes(2);
  });

  it('без sessionStorage не перезагружает', () => {
    vi.stubGlobal('sessionStorage', undefined);
    expect(reloadOnce()).toBe(false);
    expect(reload).not.toHaveBeenCalled();
  });
});
