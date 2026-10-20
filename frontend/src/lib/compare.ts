import type { Listing, ListingId } from '../api/types';

/** Экран сравнения квартир (FRONTEND-027) */
export const COMPARE_PATH = '/compare';

/** Сервер сравнивает от 2 до 3 разных квартир, иначе 422 */
export const COMPARE_MIN = 2;
export const COMPARE_MAX = 3;

/** GET /api/listings/compare?ids=a,b,c — ID в порядке выбора */
export function compareApiPath(ids: string[]): string {
  return `/api/listings/compare?ids=${ids.map(encodeURIComponent).join(',')}`;
}

/**
 * Сравнивать можно только помесячную аренду: бэкенд считает «аренду в месяц», залог
 * и коммунальные — для посуточной эти цифры были бы неверными
 */
export function canCompare(listing: Pick<Listing, 'rent_period'>): boolean {
  return listing.rent_period !== 'daily';
}

/** У этой квартиры лучшее значение в строке row */
export function isBest(best: Record<string, ListingId[]>, row: string, id: ListingId): boolean {
  return (best[row] ?? []).some((item) => String(item) === String(id));
}
