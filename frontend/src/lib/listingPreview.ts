import type { Listing } from '../api/types';

/** Столько карточек помним; самая старая вытесняется */
const PREVIEW_MAX = 200;
const previews = new Map<string, Listing>();

/**
 * Запомнить квартиру с карточки списка: по нажатию страница объявления сразу показывает
 * фото, цену и заголовок, а полный ответ GET /api/listings/{id} тихо их дополняет
 */
export function rememberListingPreview(listing: Listing): void {
  const id = String(listing.id);
  previews.delete(id);
  previews.set(id, listing);
  const oldest = previews.keys().next();
  if (previews.size > PREVIEW_MAX && !oldest.done) previews.delete(oldest.value);
}

/** Квартира с карточки, если её недавно показывали в списке */
export function listingPreview(id: string): Listing | undefined {
  return previews.get(id);
}
