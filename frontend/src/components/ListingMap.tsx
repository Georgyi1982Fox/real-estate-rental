import { useEffect, useRef } from 'react';
import { circle, divIcon, map as createMap, marker, tileLayer } from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface ListingMapProps {
  latitude: number;
  longitude: number;
  /** Точка известна — метка; известен только район — круг «примерно здесь» */
  exact: boolean;
  label: string;
}

const TILES_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
// Подпись обязательна по лицензии OpenStreetMap
const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>';
const EXACT_ZOOM = 16;
const DISTRICT_ZOOM = 14;
const DISTRICT_RADIUS_M = 700;
const PIN_SIZE = 28;

/**
 * Карта объявления: Leaflet + плитки OpenStreetMap. Грузится отдельным чанком (React.lazy).
 * Колесо мыши карту не масштабирует — страница прокручивается; пальцем карта двигается.
 */
export default function ListingMap({ latitude, longitude, exact, label }: ListingMapProps) {
  const canvasRef = useRef<HTMLDivElement>(null);

  // Leaflet рисует сам в свой контейнер — React внутрь него не заглядывает
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const center: [number, number] = [latitude, longitude];
    const view = createMap(canvas, {
      center,
      zoom: exact ? EXACT_ZOOM : DISTRICT_ZOOM,
      scrollWheelZoom: false,
    });
    tileLayer(TILES_URL, { maxZoom: 19, attribution: ATTRIBUTION }).addTo(view);
    // Цвета метки и круга — в main.css (.listing-map__*), из переменных темы
    if (exact) {
      marker(center, {
        icon: divIcon({
          className: 'listing-map__pin',
          iconSize: [PIN_SIZE, PIN_SIZE],
          iconAnchor: [PIN_SIZE / 2, PIN_SIZE],
        }),
        interactive: false,
        keyboard: false,
      }).addTo(view);
    } else {
      circle(center, {
        radius: DISTRICT_RADIUS_M,
        className: 'listing-map__area',
        interactive: false,
      }).addTo(view);
    }
    return () => {
      view.remove();
    };
  }, [latitude, longitude, exact]);

  return (
    <div
      ref={canvasRef}
      className="listing-map h-full w-full"
      role="application"
      aria-label={label}
    />
  );
}
