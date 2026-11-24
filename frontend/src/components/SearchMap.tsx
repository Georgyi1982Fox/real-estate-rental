import { useEffect, useRef, useState } from 'react';
import {
  divIcon,
  latLngBounds,
  layerGroup,
  map as createMap,
  marker,
  tileLayer,
  type LayerGroup,
  type Map as LeafletMap,
  type Marker,
} from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { DistrictNames } from '../hooks/useDistricts';
import { plural, tr } from '../lib/format';
import type { MapGroup } from '../lib/mapGroups';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import MapListingSheet from './MapListingSheet';

/** Куда смотреть, если на странице нет ни одной точки: центр города или вся Грузия */
export interface MapFallback {
  latitude: number;
  longitude: number;
  zoom: number;
}

interface SearchMapProps {
  groups: MapGroup[];
  fallback: MapFallback;
  districtNames: DistrictNames;
}

// Плитки и подпись — как в ListingMap (подпись обязательна по лицензии OpenStreetMap)
const TILES_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>';
/** Ближе не подлетаем: одна точка или дома в соседних дворах */
const FIT_MAX_ZOOM = 16;
const FIT_PADDING: [number, number] = [36, 36];
const DOT_SIZE = 22;
const BUILDING_SIZE = 32;
/** Сколько места снизу закрывает карточка: выбранная точка не должна под неё уйти */
const SHEET_COVER_PX = 190;

/**
 * Где была карта: вернулись «Назад» со страницы квартиры к тем же квартирам —
 * карта стоит, где её оставили, а не прыгает обратно на «все точки»
 */
let lastView: { signature: string; center: [number, number]; zoom: number } | undefined;

function dotIcon(group: MapGroup, active: boolean) {
  const count = group.listings.length;
  const size = count > 1 ? BUILDING_SIZE : DOT_SIZE;
  return divIcon({
    className: `search-map__dot${count > 1 ? ' search-map__dot--building' : ''}${active ? ' search-map__dot--active' : ''}`,
    html: count > 1 ? `<span>${count}</span>` : '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

/**
 * Квартиры страницы поиска на карте (FRONTEND-056): Leaflet + плитки OpenStreetMap,
 * отдельный чанк (React.lazy). Квартиры одного дома — одна точка с числом (groupByBuilding).
 * Нажали точку — карточка внизу; нажали мимо точек или ✕ — карточка закрывается.
 */
export default function SearchMap({ groups, fallback, districtNames }: SearchMapProps) {
  const { lang, t } = useI18n();
  const mt = t.home.map;
  const canvasRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const layerRef = useRef<LayerGroup | null>(null);
  const markersRef = useRef(new Map<string, Marker>());
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const selected = groups.find((group) => group.key === selectedKey);
  // Те же квартиры (тихое обновление после «Назад») — карту не трогаем
  const signature = groups
    .flatMap((group) => group.listings.map((listing) => listing.id))
    .join(',');
  const fallbackKey = `${fallback.latitude},${fallback.longitude},${fallback.zoom}`;

  // Карта создаётся один раз; Leaflet рисует сам, React внутрь контейнера не заглядывает
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const view = createMap(canvas, { scrollWheelZoom: false, zoomControl: true });
    tileLayer(TILES_URL, { maxZoom: 19, attribution: ATTRIBUTION }).addTo(view);
    layerRef.current = layerGroup().addTo(view);
    mapRef.current = view;
    view.on('click', () => setSelectedKey(null));
    const markers = markersRef.current;
    return () => {
      view.remove();
      mapRef.current = null;
      layerRef.current = null;
      markers.clear();
    };
  }, []);

  // Точки страницы: новые квартиры — карта показывает их все
  useEffect(() => {
    const view = mapRef.current;
    const layer = layerRef.current;
    if (!view || !layer) return;
    layer.clearLayers();
    markersRef.current.clear();
    for (const group of groups) {
      const count = group.listings.length;
      const first = group.listings[0];
      const point = marker([group.latitude, group.longitude], {
        icon: dotIcon(group, false),
        title: count > 1 ? plural(mt.building, count, lang) : first ? tr(first.title, lang) : '',
        riseOnHover: true,
      });
      point.on('click', () => {
        haptic('light');
        setSelectedKey(group.key);
      });
      point.addTo(layer);
      markersRef.current.set(group.key, point);
    }
    setSelectedKey((key) => (groups.some((group) => group.key === key) ? key : null));
    // groups меняются вместе с signature; язык — только подписи точек
  }, [signature, lang]);

  // Куда смотреть: где оставили (те же квартиры) или так, чтобы были видны все точки
  useEffect(() => {
    const view = mapRef.current;
    if (!view) return;
    if (lastView?.signature === signature && signature) {
      view.setView(lastView.center, lastView.zoom, { animate: false });
    } else if (groups.length === 1 && groups[0]) {
      view.setView([groups[0].latitude, groups[0].longitude], FIT_MAX_ZOOM, { animate: false });
    } else if (groups.length > 1) {
      const bounds = latLngBounds(groups.map((group) => [group.latitude, group.longitude]));
      view.fitBounds(bounds, { padding: FIT_PADDING, maxZoom: FIT_MAX_ZOOM, animate: false });
    } else {
      view.setView([fallback.latitude, fallback.longitude], fallback.zoom, { animate: false });
    }
    const remember = () => {
      const center = view.getCenter();
      lastView = { signature, center: [center.lat, center.lng], zoom: view.getZoom() };
    };
    remember();
    view.on('moveend', remember);
    return () => {
      view.off('moveend', remember);
    };
    // Не groups: тихое обновление тех же квартир не должно двигать карту
  }, [signature, fallbackKey]);

  // Выбранная точка — другим цветом и не под карточкой
  useEffect(() => {
    markersRef.current.forEach((point, key) => {
      const group = groups.find((item) => item.key === key);
      if (group) point.setIcon(dotIcon(group, key === selectedKey));
      if (key === selectedKey) point.setZIndexOffset(1000);
      else point.setZIndexOffset(0);
    });
    const view = mapRef.current;
    const point = selectedKey ? markersRef.current.get(selectedKey) : undefined;
    if (view && point) {
      // Карта видна не целиком — прокручиваем страницу, чтобы карточку не закрыло меню
      view.getContainer().closest('.search-page__map')?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
      view.panInside(point.getLatLng(), {
        paddingTopLeft: [24, 24],
        paddingBottomRight: [24, SHEET_COVER_PX],
      });
    }
  }, [selectedKey, signature]);

  return (
    // isolate: слои Leaflet (z-index до 1000) не вылезают поверх шапки и модалок
    <div className="search-map relative isolate h-full w-full overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)]">
      <div
        ref={canvasRef}
        className="listing-map search-map__canvas h-full w-full"
        role="application"
        aria-label={mt.label}
      />
      {groups.length === 0 && (
        <p className="search-map__empty pointer-events-none absolute inset-x-4 top-4 z-[1000] m-0 rounded-[var(--radius-md)] bg-[var(--surface)] px-4 py-3 text-center text-sm text-[var(--text-secondary)] shadow-[var(--shadow-md)]">
          {mt.no_points}
        </p>
      )}
      {selected && (
        // Над подписью © OpenStreetMap внизу справа
        <div className="search-map__sheet absolute inset-x-2 bottom-7 z-[1000] mx-auto max-w-md">
          <MapListingSheet
            key={selected.key}
            group={selected}
            districtNames={districtNames}
            onClose={() => setSelectedKey(null)}
          />
        </div>
      )}
    </div>
  );
}
