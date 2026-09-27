import { useCallback, useState } from 'react';

// Бэкенда для уведомлений пока нет — настройка живёт только в localStorage
const STORAGE_KEY = 'bina:notifications';

function load(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    // localStorage может быть недоступен (приватный режим)
    return false;
  }
}

/** Переключатель «Уведомления»: [включены, изменить] */
export function useNotifications(): [boolean, (enabled: boolean) => void] {
  const [enabled, setEnabledState] = useState(load);

  const setEnabled = useCallback((next: boolean) => {
    setEnabledState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next ? '1' : '0');
    } catch {
      // см. load() — значение останется до перезагрузки
    }
  }, []);

  return [enabled, setEnabled];
}
