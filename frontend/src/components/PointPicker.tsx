import { useEffect, useRef } from 'react';
import { divIcon, map as createMap, marker, tileLayer } from 'leaflet';
import type { Map as LeafletMap, Marker } from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface PointPickerProps {
  /** Выбранная точка; null — метки нет */
  latitude: number | null;
  longitude: number | null;
  /** Куда смотрит карта, пока точки нет: центр выбранного города */
  center: [number, number];
  onChange: (latitude: number, longitude: number) => void;
  label: string;
}

const TILES_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
// Подпись обязательна по лицензии OpenStreetMap
const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>';
const CITY_ZOOM = 13;
const POINT_ZOOM = 16;
const PIN_SIZE = 28;
/** Координаты с точностью около метра */
const round = (value: number) => Math.round(value * 1e5) / 1e5;

/**
 * Выбор точки на карте: нажатие ставит метку. Leaflet + плитки OpenStreetMap,
 * грузится отдельным чанком (React.lazy), как ListingMap
 */
export default function PointPicker({
  latitude,
  longitude,
  center,
  onChange,
  label,
}: PointPickerProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<LeafletMap | null>(null);
  const pinRef = useRef<Marker | null>(null);
  // Актуальный обработчик без пересоздания карты
  const changeRef = useRef(onChange);
  useEffect(() => {
    changeRef.current = onChange;
  });
  const [centerLat, centerLon] = center;

  // Leaflet рисует сам в свой контейнер — React внутрь него не заглядывает
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const view = createMap(canvas, { scrollWheelZoom: false });
    tileLayer(TILES_URL, { maxZoom: 19, attribution: ATTRIBUTION }).addTo(view);
    view.on('click', (event) => changeRef.current(round(event.latlng.lat), round(event.latlng.lng)));
    viewRef.current = view;
    return () => {
      view.remove();
      viewRef.current = null;
      pinRef.current = null;
    };
  }, []);

  // Метка и вид карты следуют за выбранной точкой; без точки — центр города
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    if (latitude === null || longitude === null) {
      pinRef.current?.remove();
      pinRef.current = null;
      view.setView([centerLat, centerLon], CITY_ZOOM);
      return;
    }
    const point: [number, number] = [latitude, longitude];
    if (pinRef.current) {
      pinRef.current.setLatLng(point);
    } else {
      // Цвет метки — в main.css (.listing-map__pin), из переменных темы
      pinRef.current = marker(point, {
        icon: divIcon({
          className: 'listing-map__pin',
          iconSize: [PIN_SIZE, PIN_SIZE],
          iconAnchor: [PIN_SIZE / 2, PIN_SIZE],
        }),
        interactive: false,
        keyboard: false,
      }).addTo(view);
    }
    // Уже приближенную карту не отдаляем
    view.setView(point, Math.max(view.getZoom() ?? 0, POINT_ZOOM));
  }, [latitude, longitude, centerLat, centerLon]);

  return (
    <div
      ref={canvasRef}
      className="listing-map point-picker h-full w-full cursor-crosshair"
      role="application"
      aria-label={label}
    />
  );
}
