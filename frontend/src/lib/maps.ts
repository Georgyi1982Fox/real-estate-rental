// Ссылки на внешние карты по точке или по тексту адреса (для окна «Открыть в картах»)

export interface MapTarget {
  latitude?: number | null;
  longitude?: number | null;
  /** Адрес текстом — если точки нет */
  query?: string;
}

export interface MapLinks {
  google: string;
  yandex: string;
}

/** Страна в конце текста адреса: иначе «Ваке» или «Руставели» найдутся не в Грузии */
const COUNTRY = 'Georgia';

function hasPoint(target: MapTarget): target is MapTarget & { latitude: number; longitude: number } {
  return Number.isFinite(target.latitude) && Number.isFinite(target.longitude);
}

/** Google Maps и Яндекс Карты; null — ни точки, ни адреса */
export function mapLinks(target: MapTarget): MapLinks | null {
  if (hasPoint(target)) {
    const { latitude, longitude } = target;
    return {
      google: `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`,
      // У Яндекса порядок обратный: долгота, широта
      yandex: `https://yandex.com/maps/?pt=${longitude},${latitude}&z=16&l=map`,
    };
  }
  const text = target.query?.trim();
  if (!text) return null;
  const query = encodeURIComponent(`${text}, ${COUNTRY}`);
  return {
    google: `https://www.google.com/maps/search/?api=1&query=${query}`,
    yandex: `https://yandex.com/maps/?text=${query}`,
  };
}
