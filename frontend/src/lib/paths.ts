// Адреса разделов, на которые ссылаются из нескольких мест

/** Аренда: главная квартир (поиск, подборки, новые объявления) — первое направление стартового экрана */
export const RENT_PATH = '/rent';

/** «Ещё» в нижней панели: Premium, размещение, инструменты, помощь, документы */
export const MORE_PATH = '/more';

/**
 * Акт приёмки квартиры (FRONTEND-024). Здесь, а не в lib/acceptance.ts, — чтобы ссылки
 * на акт не тянули в основную часть сайта весь код акта (FRONTEND-054)
 */
export const ACCEPTANCE_PATH = '/acceptance';
/** Параметр адреса: акт для объявления (`/acceptance?listing=12`) */
export const ACCEPTANCE_LISTING_PARAM = 'listing';

/** Адрес страницы акта: для объявления или без него (из профиля) */
export function acceptancePath(listingId?: string | number): string {
  if (listingId === undefined) return ACCEPTANCE_PATH;
  return `${ACCEPTANCE_PATH}?${ACCEPTANCE_LISTING_PARAM}=${encodeURIComponent(String(listingId))}`;
}
