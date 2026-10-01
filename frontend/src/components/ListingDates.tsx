import { fill, listingTime } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';

interface ListingDatesProps {
  publishedAt?: string | null;
  updatedAt?: string | null;
}

/** «Опубликовано 31 августа · обновлено вчера». Нет дат — блока нет */
export default function ListingDates({ publishedAt, updatedAt }: ListingDatesProps) {
  const { lang, t } = useI18n();
  const lt = t.listing;
  const published = publishedAt ? listingTime(publishedAt, lang, lt.hours_ago) : '';
  // Объявление не меняли (обновлено тогда же, когда опубликовано) — вторую дату не повторяем
  const unchanged =
    Boolean(publishedAt && updatedAt) &&
    new Date(updatedAt ?? '').getTime() <= new Date(publishedAt ?? '').getTime();
  const updated = updatedAt && !unchanged ? listingTime(updatedAt, lang, lt.hours_ago) : '';

  if (!published && !updated) return null;

  return (
    <p className="listing-dates flex flex-wrap gap-x-2 gap-y-1 text-xs text-[var(--text-secondary)]">
      {published && <time dateTime={publishedAt ?? ''}>{fill(lt.published, published)}</time>}
      {published && updated && <span aria-hidden="true">·</span>}
      {updated && <time dateTime={updatedAt ?? ''}>{fill(lt.updated, updated)}</time>}
    </p>
  );
}
