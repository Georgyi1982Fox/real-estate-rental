import { fill, listingTime, plural } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';

interface ListingDatesProps {
  publishedAt?: string | null;
  updatedAt?: string | null;
  /** Просмотры на Bina.ai; null — счётчика нет (в списках), не показываем */
  views?: number | null;
}

/** «Опубликовано 31 августа · обновлено вчера · 👁 123 просмотра». Нечего показать — блока нет */
export default function ListingDates({ publishedAt, updatedAt, views }: ListingDatesProps) {
  const { lang, t } = useI18n();
  const lt = t.listing;
  const published = publishedAt ? listingTime(publishedAt, lang, lt.hours_ago) : '';
  // Объявление не меняли (обновлено тогда же, когда опубликовано) — вторую дату не повторяем
  const unchanged =
    Boolean(publishedAt && updatedAt) &&
    new Date(updatedAt ?? '').getTime() <= new Date(publishedAt ?? '').getTime();
  const updated = updatedAt && !unchanged ? listingTime(updatedAt, lang, lt.hours_ago) : '';

  const viewsText = typeof views === 'number' && views > 0 ? plural(lt.views, views, lang) : '';

  if (!published && !updated && !viewsText) return null;

  return (
    <p className="listing-dates flex flex-wrap gap-x-2 gap-y-1 text-xs text-[var(--text-secondary)]">
      {published && <time dateTime={publishedAt ?? ''}>{fill(lt.published, published)}</time>}
      {published && updated && <span aria-hidden="true">·</span>}
      {updated && <time dateTime={updatedAt ?? ''}>{fill(lt.updated, updated)}</time>}
      {(published || updated) && viewsText && <span aria-hidden="true">·</span>}
      {viewsText && (
        <span className="listing-dates__views">
          <span aria-hidden="true">👁 </span>
          {viewsText}
        </span>
      )}
    </p>
  );
}
