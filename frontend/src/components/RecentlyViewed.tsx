import { Link } from 'react-router-dom';
import type { ViewHistory } from '../api/types';
import { useApi } from '../hooks/useApi';
import type { DistrictNames } from '../hooks/useDistricts';
import { HISTORY_PATH, HOME_HISTORY_LIMIT, historyApiPath } from '../lib/history';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import ListingCard from './ListingCard';

// Мобильный: горизонтальная лента со свайпом; от 640px — обычная сетка
const TRACK_CLASS =
  'recently-viewed__track no-scrollbar -mx-4 flex list-none snap-x snap-mandatory scroll-px-4 gap-4 overflow-x-auto px-4 pb-2 pt-1 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-x-visible sm:px-0 lg:grid-cols-3';
const ITEM_CLASS =
  'recently-viewed__item w-[80%] max-w-xs shrink-0 snap-start sm:w-auto sm:max-w-none';

/**
 * «🕘 Вы смотрели» на главной (FRONTEND-043). Только для вошедших; пока истории нет
 * (или она не загрузилась) — блока нет, главная выглядит как раньше
 */
export default function RecentlyViewed({ districtNames }: { districtNames: DistrictNames }) {
  const { t } = useI18n();
  const ht = t.history;
  const { user } = useAuth();
  const { data } = useApi<ViewHistory>(user ? historyApiPath(HOME_HISTORY_LIMIT) : null, {
    // «Назад» из квартиры: лента сразу на месте, затем тихо обновляется
    remember: true,
  });
  const items = data?.items ?? [];

  if (items.length === 0) return null;

  return (
    <section
      className="recently-viewed flex flex-col gap-4"
      aria-labelledby="recently-viewed-title"
    >
      <header className="flex items-baseline justify-between gap-3">
        <h2 id="recently-viewed-title" className="text-xl font-bold tracking-tight">
          <span aria-hidden="true">🕘 </span>
          {ht.home_title}
        </h2>
        <Link
          to={HISTORY_PATH}
          className="recently-viewed__all rounded-[var(--radius-sm)] text-sm font-semibold text-[var(--text-primary)] underline underline-offset-2 hover:text-[var(--text-secondary)]"
          onClick={() => haptic('light')}
        >
          {t.hub.see_all}
        </Link>
      </header>
      <ul className={TRACK_CLASS}>
        {items.map(({ listing }) => (
          <li key={listing.id} className={ITEM_CLASS}>
            <ListingCard listing={listing} districtNames={districtNames} headingLevel="h3" />
          </li>
        ))}
      </ul>
    </section>
  );
}
