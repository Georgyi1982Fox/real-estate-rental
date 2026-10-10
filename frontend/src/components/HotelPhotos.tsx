import { useRef, useState } from 'react';
import type { ChangeEvent } from 'react';
import { apiDelete, apiUpload } from '../api/client';
import type { MyHotel } from '../api/types';
import { fill } from '../lib/format';
import { HOTEL_PHOTO_MAX_BYTES, HOTEL_PHOTOS_MAX, hotelErrorTexts } from '../lib/hotelForm';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import Icon from './Icon';

const PHOTO_TYPES = 'image/jpeg,image/png,image/webp';

interface HotelPhotosProps {
  hotel: MyHotel;
  /** Сервер после каждого фото отдаёт объект целиком */
  onChange: (hotel: MyHotel) => void;
}

/**
 * Шаг 7 формы размещения: фото объекта. Загружаются по одному (тело запроса — файл),
 * до 20 штук; удаляются по номеру в списке
 */
export default function HotelPhotos({ hotel, onChange }: HotelPhotosProps) {
  const { t } = useI18n();
  const ft = t.hotel_form;
  const showToast = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const images = hotel.images ?? [];
  const path = `/api/my/hotels/${hotel.id}/photos`;

  const fail = (error: unknown) => {
    haptic('error');
    showToast(hotelErrorTexts(error, ft, 0)[0] ?? ft.errors.generic, 'error');
  };

  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const free = HOTEL_PHOTOS_MAX - images.length;
    const files = Array.from(event.target.files ?? []);
    // Тот же файл можно выбрать снова
    event.target.value = '';
    if (files.length === 0) return;
    if (files.length > free) showToast(ft.errors.too_many_photos, 'error');
    setBusy(true);
    try {
      // По одному: сервер принимает одно фото за запрос
      for (const file of files.slice(0, free)) {
        if (file.size > HOTEL_PHOTO_MAX_BYTES) {
          showToast(ft.errors.bad_photo, 'error');
          continue;
        }
        onChange(await apiUpload<MyHotel>(path, file));
      }
      haptic('success');
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (index: number) => {
    haptic('light');
    setBusy(true);
    try {
      onChange(await apiDelete<MyHotel>(`${path}/${index}`));
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="hotel-photos flex flex-col gap-3" aria-label={ft.steps.photos} aria-busy={busy}>
      <p className="m-0 flex justify-between gap-3 text-xs text-[var(--text-secondary)]">
        <span>{fill(ft.photos_hint, HOTEL_PHOTOS_MAX)}</span>
        <span className="shrink-0 tabular-nums">
          {images.length} / {HOTEL_PHOTOS_MAX}
        </span>
      </p>

      {images.length > 0 && (
        <ul className="m-0 grid list-none grid-cols-3 gap-2 p-0 sm:grid-cols-4">
          {images.map((image, index) => (
            <li
              key={image}
              className="hotel-photos__item relative aspect-square overflow-hidden rounded-[var(--radius-md)] bg-[var(--surface-hover)]"
            >
              <img
                src={image}
                alt={fill(t.gallery.go_to, index + 1)}
                loading="lazy"
                className="h-full w-full object-cover"
              />
              <button
                type="button"
                className="absolute right-1 top-1 grid size-9 place-items-center rounded-full bg-[var(--surface)]/90 text-[var(--text-primary)] shadow-[var(--shadow-sm)] backdrop-blur-sm hover:bg-[var(--surface)] active:scale-[.95] disabled:opacity-60"
                aria-label={fill(ft.photo_delete, index + 1)}
                disabled={busy}
                onClick={() => void remove(index)}
              >
                <Icon name="trash" className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {images.length < HOTEL_PHOTOS_MAX && (
        <>
          <input
            ref={inputRef}
            type="file"
            accept={PHOTO_TYPES}
            multiple
            className="sr-only"
            tabIndex={-1}
            aria-hidden="true"
            onChange={(event) => void upload(event)}
          />
          <button
            type="button"
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-[var(--radius-md)] border border-dashed border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-hover)] active:scale-[.98] disabled:opacity-70"
            disabled={busy}
            onClick={() => inputRef.current?.click()}
          >
            {busy ? <span className="spinner" aria-hidden="true" /> : <Icon name="image" className="size-4" />}
            {busy ? ft.uploading : ft.add_photo}
          </button>
        </>
      )}
    </section>
  );
}
