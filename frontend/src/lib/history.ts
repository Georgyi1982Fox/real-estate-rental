// «Недавно смотрели» (FRONTEND-043, бэкенд — TASK-075): бэкенд сам записывает просмотр,
// когда вошедший человек открывает квартиру; здесь — только адреса

export const HISTORY_PATH = '/history';

/** Все запросы истории начинаются так (кэш useApi сбрасываем по этому началу) */
export const HISTORY_API = '/api/history';

/** Сколько квартир показывать: лента на главной и вся страница (бэкенд хранит 100) */
export const HOME_HISTORY_LIMIT = 20;
export const PAGE_HISTORY_LIMIT = 100;

export function historyApiPath(limit: number): string {
  return `${HISTORY_API}?limit=${limit}`;
}
