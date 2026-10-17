import { useEffect, useRef } from 'react';
import type { Recommendations as RecommendationsData } from '../api/types';
import { useApi } from '../hooks/useApi';
import type { DistrictNames } from '../hooks/useDistricts';
import { useFavorites, useFavoritesServerVersion } from '../hooks/useFavorites';
import { usesServerFavorites } from '../lib/session';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import ListingCard from './ListingCard';
import Skeleton from './Skeleton';

const RECOMMENDATIONS_PATH = '/api/recommendations?limit=10';
const SKELETON_COUNT = 3;
// Мобильный: горизонтальная лента со свайпом; от 640px — обычная сетка
const TRACK_CLASS =
  'recommendations__track no-scrollbar -mx-4 flex list-none snap-x snap-mandatory scroll-px-4 gap-4 overflow-x-auto px-4 pb-2 pt-1 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-x-visible sm:px-0 lg:grid-cols-3';
const ITEM_CLASS =
  'recommendations__item w-[80%] max-w-xs shrink-0 snap-start sm:w-auto sm:max-w-none';
const HINT_CLASS =
  'rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] px-4 py-8 text-center text-sm text-[var(--text-secondary)]';

interface RecommendationsProps {
  districtNames: DistrictNames;
  /**
   * На главной: без подсказок и скелетонов — блок появляется, только когда есть что
   * показать, иначе главная выглядит как раньше
   */
  quiet?: boolean;
}

/**
 * «✨ Вам может понравиться» (FRONTEND-041): квартиры, похожие на избранное. Избранное для
 * подбора хранится на сервере, поэтому блок — только для вошедших через Telegram
 */
export default function Recommendations({ districtNames, quiet = false }: RecommendationsProps) {
  const { t } = useI18n();
  const rt = t.recommend;
  const { user } = useAuth();
  const { isFavorite } = useFavorites();
  const enabled = Boolean(user) && usesServerFavorites();
  const { data, loading, reload } = useApi<RecommendationsData>(
    enabled ? RECOMMENDATIONS_PATH : null,
    // «Назад» из квартиры: лента сразу на месте, затем тихо обновляется
    { remember: true },
  );

  // Сервер подтвердил изменение избранного — подбор мог измениться
  const serverVersion = useFavoritesServerVersion();
  const shownVersion = useRef(serverVersion);
  useEffect(() => {
    if (shownVersion.current === serverVersion) return;
    shownVersion.current = serverVersion;
    reload();
  }, [serverVersion, reload]);

  if (!enabled) return null;
  // Только что добавленная в избранное квартира пропадает из ленты сразу, не дожидаясь сервера
  const items = data?.items.filter((listing) => !isFavorite(listing.id)) ?? [];
  if (quiet && items.length === 0) return null;
  // Не загрузилось — блока нет: это подсказка, а не главное на странице
  if (!data && !loading) return null;

  return (
    <section
      className="recommendations flex flex-col gap-4"
      aria-labelledby="recommendations-title"
      aria-busy={loading}
    >
      <h2 id="recommendations-title" className="text-xl font-bold tracking-tight">
        <span aria-hidden="true">✨ </span>
        {rt.title}
      </h2>

      {loading && (
        <ul className={TRACK_CLASS}>
          {Array.from({ length: SKELETON_COUNT }, (_, index) => (
            <li key={index} className={ITEM_CLASS}>
              <Skeleton />
            </li>
          ))}
        </ul>
      )}

      {data && data.based_on === 0 && <p className={HINT_CLASS}>{rt.no_favorites}</p>}

      {data && data.based_on > 0 && items.length === 0 && <p className={HINT_CLASS}>{rt.empty}</p>}

      {items.length > 0 && (
        <ul className={TRACK_CLASS}>
          {items.map((listing) => (
            <li key={listing.id} className={ITEM_CLASS}>
              <ListingCard listing={listing} districtNames={districtNames} headingLevel="h3" />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
