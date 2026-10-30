import { useRef, useState } from 'react';
import type { ChangeEvent } from 'react';
import { ApiError, apiDelete, apiUpload } from '../api/client';
import { fill, fillVars } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import Icon from './Icon';

const PHOTO_TYPES = 'image/jpeg,image/png,image/webp';

interface PhotoUploaderProps<Saved> {
  images: string[];
  /** POST сюда — новое фото, DELETE {path}/{номер} — удалить */
  path: string;
  max: number;
  maxBytes: number;
  /** Сервер после каждого фото отдаёт объект целиком */
  onChange: (saved: Saved) => void;
  errorText: (error: unknown) => string;
  label: string;
  hint: string;
  addLabel: string;
  /** Подпись на время загрузки; может содержать {n} и {total} */
  uploadingLabel: string;
  /** Подпись кнопки удаления, {n} — номер фото */
  deleteLabel: string;
  tooManyText: string;
  tooBigText: string;
}

/** Фото объекта: загрузка по одному (тело запроса — файл), превью и удаление по номеру */
export default function PhotoUploader<Saved>({
  images,
  path,
  max,
  maxBytes,
  onChange,
  errorText,
  label,
  hint,
  addLabel,
  uploadingLabel,
  deleteLabel,
  tooManyText,
  tooBigText,
}: PhotoUploaderProps<Saved>) {
  const { t } = useI18n();
  const showToast = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState({ n: 0, total: 0 });

  const fail = (text: string) => {
    haptic('error');
    showToast(text, 'error');
  };

  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const free = max - images.length;
    const files = Array.from(event.target.files ?? []);
    // Тот же файл можно выбрать снова
    event.target.value = '';
    if (files.length === 0) return;
    if (files.length > free) fail(tooManyText);
    const queue = files.slice(0, free);
    let uploaded = false;
    setBusy(true);
    try {
      // По одному: сервер принимает одно фото за запрос
      for (const [index, file] of queue.entries()) {
        setProgress({ n: index + 1, total: queue.length });
        if (file.size > maxBytes) {
          fail(tooBigText);
          continue;
        }
        try {
          onChange(await apiUpload<Saved>(path, file));
          uploaded = true;
        } catch (error) {
          fail(errorText(error));
          // Сервер отверг один файл (422) — остальные ещё можно загрузить
          if (!(error instanceof ApiError && error.status === 422)) break;
        }
      }
      if (uploaded) haptic('success');
    } finally {
      setBusy(false);
    }
  };

  const remove = async (index: number) => {
    haptic('light');
    setBusy(true);
    setProgress({ n: 0, total: 0 });
    try {
      onChange(await apiDelete<Saved>(`${path}/${index}`));
    } catch (error) {
      fail(errorText(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="photo-uploader flex flex-col gap-3" aria-label={label} aria-busy={busy}>
      <p className="m-0 flex justify-between gap-3 text-xs text-[var(--text-secondary)]">
        <span>{hint}</span>
        <span className="shrink-0 tabular-nums">
          {images.length} / {max}
        </span>
      </p>

      {images.length > 0 && (
        <ul className="m-0 grid list-none grid-cols-3 gap-2 p-0 sm:grid-cols-4">
          {images.map((image, index) => (
            <li
              key={image}
              className="photo-uploader__item relative aspect-square overflow-hidden rounded-[var(--radius-md)] bg-[var(--surface-hover)]"
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
                aria-label={fill(deleteLabel, index + 1)}
                disabled={busy}
                onClick={() => void remove(index)}
              >
                <Icon name="trash" className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {images.length < max && (
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
            {busy ? (
              <span className="spinner" aria-hidden="true" />
            ) : (
              <Icon name="image" className="size-4" />
            )}
            {busy ? fillVars(uploadingLabel, progress) : addLabel}
          </button>
        </>
      )}
    </section>
  );
}
