/** Уменьшение картинки в браузере перед загрузкой (FRONTEND-049) */

export interface ShrinkOptions {
  /** Длинная сторона результата, px */
  maxSide: number;
  /** PNG / WebP (возможна прозрачность) сохранить как PNG, а не JPEG */
  keepTransparency?: boolean;
}

/** Фото квартиры или гостиницы: на экране больше не нужно */
export const PHOTO_SHRINK: ShrinkOptions = { maxSide: 1600 };
/** Логотип агентства */
export const LOGO_SHRINK: ShrinkOptions = { maxSide: 512, keepTransparency: true };

/** Меньше этого веса и в пределах maxSide — файл уходит как есть */
const SMALL_BYTES = 1.5 * 1024 * 1024;
const JPEG_QUALITY = 0.85;
const TRANSPARENT_TYPES = new Set(['image/png', 'image/webp']);

type Source = ImageBitmap | HTMLImageElement;

/** Открывает файл с поворотом, как на телефоне (EXIF); null — браузер не смог */
async function decode(file: Blob): Promise<Source | null> {
  if (typeof createImageBitmap === 'function') {
    try {
      return await createImageBitmap(file, { imageOrientation: 'from-image' });
    } catch {
      // Ниже — запасной путь через <img> (он тоже поворачивает по EXIF)
    }
  }
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    return img;
  } catch {
    return null;
  } finally {
    URL.revokeObjectURL(url);
  }
}

function sizeOf(source: Source): { width: number; height: number } {
  return source instanceof HTMLImageElement
    ? { width: source.naturalWidth, height: source.naturalHeight }
    : { width: source.width, height: source.height };
}

function toBlob(canvas: HTMLCanvasElement, type: string, quality?: number): Promise<Blob | null> {
  return new Promise((resolve) => canvas.toBlob(resolve, type, quality));
}

/**
 * Уменьшает картинку до options.maxSide по длинной стороне (JPEG ~0.85, для логотипа
 * с прозрачностью — PNG). Если файл уже маленький, браузер не смог его открыть или
 * результат не легче оригинала — возвращает оригинал: сервер сам скажет, если это не фото.
 */
export async function shrinkImage(file: File, options: ShrinkOptions): Promise<Blob> {
  const source = await decode(file);
  if (!source) return file;
  try {
    const { width, height } = sizeOf(source);
    if (!width || !height) return file;
    const longSide = Math.max(width, height);
    if (longSide <= options.maxSide && file.size <= SMALL_BYTES) return file;

    const scale = Math.min(1, options.maxSide / longSide);
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(width * scale));
    canvas.height = Math.max(1, Math.round(height * scale));
    const context = canvas.getContext('2d');
    if (!context) return file;

    const png = options.keepTransparency === true && TRANSPARENT_TYPES.has(file.type);
    if (!png) {
      // В JPEG нет прозрачности: прозрачные места — белые, а не чёрные
      context.fillStyle = '#fff';
      context.fillRect(0, 0, canvas.width, canvas.height);
    }
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = 'high';
    context.drawImage(source, 0, 0, canvas.width, canvas.height);

    const blob = png
      ? await toBlob(canvas, 'image/png')
      : await toBlob(canvas, 'image/jpeg', JPEG_QUALITY);
    if (!blob || blob.size === 0) return file;
    // Уже сжатое фото того же размера могло стать тяжелее — тогда оригинал
    if (scale === 1 && blob.size >= file.size) return file;
    return blob;
  } catch {
    return file;
  } finally {
    if (!(source instanceof HTMLImageElement)) source.close();
  }
}
