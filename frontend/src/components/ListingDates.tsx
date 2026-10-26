import type { ListingId } from '../api/types';
import { fill, listingTime } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import ViewsBadge from './ViewsBadge';

interface ListingDatesProps {
  listingId: ListingId;
  publishedAt?: string | null;
  updatedAt?: string | null;
  /** Просмотры на Bina.ai; null или 0 — не показываем */
  views?: number | null;
}

/**
 * «Опубликовано 31 августа · обновлено вчера · 👁 123 просмотра». Нажатие на просмотры —
 * подсказка с подробностями (FRONTEND-046). Нечего показать — блока нет
 */
export default function ListingDates({
  listingId,
  publishedAt,
  updatedAt,
  views,
}: ListingDatesProps) {
  const { lang, t } = useI18n();
  const lt = t.listing;
  const published = publishedAt ? listingTime(publishedAt, lang, lt.hours_ago) : '';
  // Объявление не меняли (обновлено тогда же, когда опубликовано) — вторую дату не повторяем
  const unchanged =
    Boolean(publishedAt && updatedAt) &&
    new Date(updatedAt ?? '').getTime() <= new Date(publishedAt ?? '').getTime();
  const updated = updatedAt && !unchanged ? listingTime(updatedAt, lang, lt.hours_ago) : '';

  const viewCount = typeof views === 'number' ? views : 0;

  if (!published && !updated && viewCount <= 0) return null;

  return (
    // relative: подсказка просмотров раскрывается под строкой на всю её ширину
    <div className="listing-dates relative flex flex-wrap gap-x-2 gap-y-1 text-xs text-[var(--text-secondary)]">
      {published && <time dateTime={publishedAt ?? ''}>{fill(lt.published, published)}</time>}
      {published && updated && <span aria-hidden="true">·</span>}
      {updated && <time dateTime={updatedAt ?? ''}>{fill(lt.updated, updated)}</time>}
      {(published || updated) && viewCount > 0 && <span aria-hidden="true">·</span>}
      {viewCount > 0 && (
        <ViewsBadge
          listingId={listingId}
          views={viewCount}
          long
          placement="below"
          className="listing-dates__views"
        />
      )}
    </div>
  );
}
