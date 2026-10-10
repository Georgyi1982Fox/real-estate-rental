import { Suspense, lazy, useState } from 'react';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

// Leaflet (~150 КБ) нужен только здесь и на карте объявления — отдельный чанк
const PointPicker = lazy(() => import('./PointPicker'));

const BUTTON_CLASS =
  'inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-hover)] active:scale-[.98] disabled:opacity-60';

interface HotelPointFieldProps {
  latitude: number | null;
  longitude: number | null;
  /** Центр выбранного города: туда смотрит карта, пока точки нет */
  center: [number, number];
  /** null — метку убрали */
  onChange: (point: { latitude: number; longitude: number } | null) => void;
}

/** «Точка на карте»: нажатие на карту ставит метку, «Моё местоположение» — по геолокации */
export default function HotelPointField({
  latitude,
  longitude,
  center,
  onChange,
}: HotelPointFieldProps) {
  const { t } = useI18n();
  const ft = t.hotel_form;
  const [locating, setLocating] = useState(false);
  const [failed, setFailed] = useState(false);
  const hasPoint = latitude !== null && longitude !== null;

  const locate = () => {
    haptic('light');
    setFailed(false);
    if (!('geolocation' in navigator)) {
      setFailed(true);
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setLocating(false);
        haptic('success');
        onChange({ latitude: coords.latitude, longitude: coords.longitude });
      },
      () => {
        setLocating(false);
        setFailed(true);
      },
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  };

  return (
    <fieldset className="hotel-point m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
      <legend className="mb-1.5 p-0 text-sm font-medium">{ft.point}</legend>
      <p className="m-0 text-xs text-[var(--text-secondary)]">{ft.point_hint}</p>
      {/* isolate: слои Leaflet (z-index до 1000) не вылезают поверх шапки и модалок */}
      <div className="hotel-point__canvas isolate h-64 w-full overflow-hidden rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-hover)]">
        <Suspense fallback={null}>
          <PointPicker
            latitude={latitude}
            longitude={longitude}
            center={center}
            label={ft.point}
            onChange={(lat, lon) => {
              haptic('selection');
              setFailed(false);
              onChange({ latitude: lat, longitude: lon });
            }}
          />
        </Suspense>
      </div>
      <div className="hotel-point__actions flex flex-wrap gap-2">
        <button
          type="button"
          className={BUTTON_CLASS}
          disabled={locating}
          aria-busy={locating}
          onClick={locate}
        >
          {locating ? (
            <span className="spinner" aria-hidden="true" />
          ) : (
            <Icon name="locate" className="size-4" />
          )}
          {ft.my_location}
        </button>
        {hasPoint && (
          <button
            type="button"
            className={BUTTON_CLASS}
            onClick={() => {
              haptic('light');
              onChange(null);
            }}
          >
            <Icon name="close" className="size-4" />
            {ft.point_clear}
          </button>
        )}
      </div>
      {failed && (
        <p className="m-0 text-xs font-medium text-[var(--danger)]" role="alert">
          {ft.location_error}
        </p>
      )}
    </fieldset>
  );
}
