import { useMemo } from 'react';
import type { District, ListResponse, Localized } from '../api/types';
import { useApi } from './useApi';

export type DistrictNames = Record<string, Localized>;

/** Список районов + словарь {district_id: {ka, ru, en}} для карточек */
export function useDistricts() {
  const { data } = useApi<ListResponse<District>>('/api/districts');
  const districts = useMemo(() => data?.items ?? [], [data]);
  const names = useMemo<DistrictNames>(
    () => Object.fromEntries(districts.map((district) => [district.id, district.name])),
    [districts],
  );
  return { districts, names };
}
