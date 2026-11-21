// «📉 Цена снижена» (FRONTEND-055): прежняя цена и на сколько процентов подешевело

import type { Listing } from '../api/types';

export interface PriceDrop {
  /** Прежняя цена, в той же валюте, что listing.price */
  oldPrice: number;
  /** На сколько процентов подешевело, от прежней цены, округлено; меньше 1 % — 0 */
  percent: number;
  /** Когда снизилась (ISO); бэкенд не прислал — null */
  droppedAt: string | null;
}

/**
 * Снижение цены за последние 30 дней — бэкенд присылает old_price только тогда.
 * Нет old_price или он не больше текущей цены — null
 */
export function priceDrop(
  listing: Pick<Listing, 'price' | 'old_price' | 'price_dropped_at'>,
): PriceDrop | null {
  const oldPrice = Number(listing.old_price);
  const price = Number(listing.price);
  if (listing.old_price == null || !Number.isFinite(oldPrice) || !Number.isFinite(price)) {
    return null;
  }
  if (oldPrice <= price || oldPrice <= 0) return null;
  return {
    oldPrice,
    percent: Math.round(((oldPrice - price) / oldPrice) * 100),
    droppedAt: listing.price_dropped_at ?? null,
  };
}
