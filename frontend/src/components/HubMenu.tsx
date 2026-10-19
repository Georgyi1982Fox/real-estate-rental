import { useId } from 'react';
import { useFavorites } from '../hooks/useFavorites';
import { useUnreadCount } from '../hooks/useNotificationFeed';
import type { Strings } from '../i18n/strings';
import { fill } from '../lib/format';
import { DAILY_SEARCH_PATH } from '../lib/searchFilters';
import { useI18n } from '../providers/I18nProvider';
import HubTile from './HubTile';
import type { HubTone } from './HubTile';
import type { IconName } from './Icon';

type TileKey = keyof Strings['hub']['tiles'];
type GroupKey = Exclude<keyof Strings['hub']['groups'], 'main'>;

interface TileConfig {
  key: TileKey;
  icon: IconName;
  /** Страница приложения; разделы без своей страницы ведут на заглушку «Скоро» */
  to?: string;
  /** Раздел, который работает только в боте */
  href?: string;
  /**
   * Класс периодической анимации иконки (main.css). Сердце бьётся само (.heart-beat в Icon),
   * остальным иконкам анимации добавляются сюда по одной
   */
  motion?: string;
}

interface GroupConfig {
  key: GroupKey;
  tone: HubTone;
  tiles: TileConfig[];
}

// Первый ряд — как искать: на месяц, посуточно, своими словами
const HERO_TILES: TileConfig[] = [
  { key: 'search', icon: 'search', to: '/search' },
  { key: 'daily', icon: 'bed', to: DAILY_SEARCH_PATH },
  { key: 'smart', icon: 'sparkles', to: '/smart' },
];
/** Три плитки в ряд и на телефоне: меню короткое, остальное — в «Ещё» */
const GRID_CLASS = 'grid grid-cols-3 gap-2';

// Своё: избранное, поиски с уведомлениями. Premium, размещение, помощь и документы — в «Ещё»
const GROUPS: GroupConfig[] = [
  {
    key: 'mine',
    tone: 'search',
    tiles: [
      { key: 'favorites', icon: 'heart', to: '/favorites' },
      { key: 'searches', icon: 'bookmark', to: '/searches' },
      // Колокольчик качается всегда, а не только при непрочитанных (в шапке — только при них)
      { key: 'notifications', icon: 'bell', to: '/notifications', motion: 'bell-ring' },
    ],
  },
];

const NOTIFICATIONS_BADGE_MAX = 9;
const FAVORITES_BADGE_MAX = 99;

/** Меню главной аренды: ряд плиток поиска и своё (избранное, поиски, уведомления) */
export default function HubMenu() {
  const { t } = useI18n();
  const ht = t.hub;
  const baseId = useId();
  const unread = useUnreadCount();
  const { count: favorites } = useFavorites();

  /** Счётчик на иконке: непрочитанные уведомления и число квартир в избранном */
  const tileBadge = (key: TileKey): { count: number; max: number; label?: string } => {
    if (key === 'notifications') {
      return {
        count: unread,
        max: NOTIFICATIONS_BADGE_MAX,
        label: unread > 0 ? fill(t.header.notifications_count, unread) : undefined,
      };
    }
    if (key === 'favorites') {
      return {
        count: favorites,
        max: FAVORITES_BADGE_MAX,
        label: favorites > 0 ? fill(t.header.favorites_count, favorites) : undefined,
      };
    }
    return { count: 0, max: 0 };
  };

  const renderTile = (tile: TileConfig, tone: HubTone) => {
    const badge = tileBadge(tile.key);
    return (
      <HubTile
        icon={tile.icon}
        title={ht.tiles[tile.key].title}
        text={ht.tiles[tile.key].text}
        tone={tone}
        to={tile.to}
        href={tile.href}
        badge={badge.count}
        badgeMax={badge.max}
        iconClass={tile.motion}
        label={badge.label}
      />
    );
  };

  return (
    <nav className="hub-menu flex flex-col gap-4" aria-label={ht.menu}>
      <ul className={`hub-menu__heroes ${GRID_CLASS}`} aria-label={ht.groups.main}>
        {HERO_TILES.map((tile) => (
          <li key={tile.key} className="min-w-0">
            {renderTile(tile, 'hero')}
          </li>
        ))}
      </ul>

      {/* Каждая группа — с новой строки, и на телефоне, и на компьютере */}
      {GROUPS.map((group) => {
        const titleId = `${baseId}-${group.key}`;
        return (
          <section
            key={group.key}
            className="hub-menu__group flex min-w-0 flex-col gap-1"
            aria-labelledby={titleId}
          >
            <h2
              id={titleId}
              className="hub-menu__group-title px-1 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]"
            >
              {ht.groups[group.key]}
            </h2>
            <ul className={GRID_CLASS}>
              {group.tiles.map((tile) => (
                <li key={tile.key} className="min-w-0">
                  {renderTile(tile, group.tone)}
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </nav>
  );
}
