import { useMemo } from 'react';
import type { HotelOptions } from '../api/types';
import {
  HOTEL_AMENITY_CODES,
  HOTEL_KIND_CODES,
  HOTEL_ROOM_KIND_CODES,
  hotelAmenityName,
  hotelKindName,
  knownCodes,
  roomKindName,
} from '../i18n/hotels';
import { useApi } from './useApi';

/**
 * Коды из GET /api/hotels/options для фильтров и формы: типы объекта, удобства и типы номеров
 * в порядке бэкенда.
 * Кода без названия во фронтенде в списке нет; сервер не ответил — коды из словаря
 */
export function useHotelOptions() {
  const { data } = useApi<HotelOptions>('/api/hotels/options', { remember: true });

  return useMemo(
    () => ({
      options: data,
      kinds: knownCodes(data?.kinds, HOTEL_KIND_CODES, hotelKindName),
      amenities: knownCodes(data?.amenities, HOTEL_AMENITY_CODES, hotelAmenityName),
      roomKinds: knownCodes(data?.room_kinds, HOTEL_ROOM_KIND_CODES, roomKindName),
    }),
    [data],
  );
}
