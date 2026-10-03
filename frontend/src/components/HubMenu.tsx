import { useId } from 'react';
import { useFavorites } from '../hooks/useFavorites';
import { useUnreadCount } from '../hooks/useNotificationFeed';
import { useSubscription } from '../hooks/useSubscription';
import type { Strings } from '../i18n/strings';
import { botSectionUrl } from '../lib/config';
import { fill, formatDate } from '../lib/format';
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

const SEARCH_TILE: TileConfig = { key: 'search', icon: 'search', to: '/search' };
const DAILY_TILE: TileConfig = { key: 'daily', icon: 'bed', to: '/daily' };

// Группы — как в главном меню бота
const GROUPS: GroupConfig[] = [
  {
    key: 'search',
    tone: 'search',
    tiles: [
      { key: 'smart', icon: 'sparkles', to: '/smart' },
      { key: 'favorites', icon: 'heart', to: '/favorites' },
      { key: 'searches', icon: 'bookmark', to: '/searches' },
      // Колокольчик качается всегда, а не только при непрочитанных (в шапке — только при них)
      { key: 'notifications', icon: 'bell', to: '/notifications', motion: 'bell-ring' },
    ],
  },
  {
    key: 'owners',
    tone: 'owner',
    tiles: [{ key: 'owner', icon: 'home_plus', to: '/my-listings' }],
  },
  {
    key: 'benefits',
    tone: 'benefit',
    tiles: [
      { key: 'premium', icon: 'crown', to: '/premium' },
      { key: 'invite', icon: 'gift', to: '/invite' },
    ],
  },
  {
    key: 'housing',
    tone: 'housing',
    tiles: [{ key: 'rent', icon: 'calendar', href: botSectionUrl('rent') }],
  },
  {
    key: 'more',
    tone: 'more',
    tiles: [
      { key: 'profile', icon: 'user', to: '/profile' },
      { key: 'help', icon: 'help', to: '/help' },
      { key: 'support', icon: 'message', href: botSectionUrl('support') },
      { key: 'terms', icon: 'file', to: '/legal/terms' },
      { key: 'privacy', icon: 'lock', to: '/legal/privacy' },
    ],
  },
];

const NOTIFICATIONS_BADGE_MAX = 9;
const FAVORITES_BADGE_MAX = 99;

/** Главное меню: две крупные плитки поиска и сетка разделов по группам */
export default function HubMenu() {
  const { lang, t } = useI18n();
  const ht = t.hub;
  const baseId = useId();
  const unread = useUnreadCount();
  const { count: favorites } = useFavorites();
  const { subscription } = useSubscription();

  const premiumUntil =
    subscription?.is_premium && subscription.expires_at
      ? formatDate(subscription.expires_at, lang)
      : '';

  /** Подпись плитки: у Premium с подпиской — срок действия */
  const tileText = (key: TileKey): string =>
    key === 'premium' && premiumUntil ? fill(ht.premium_until, premiumUntil) : ht.tiles[key].text;

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

  const renderTile = (tile: TileConfig, tone: HubTone, large = false) => {
    const badge = tileBadge(tile.key);
    return (
      <HubTile
        icon={tile.icon}
        title={ht.tiles[tile.key].title}
        text={tileText(tile.key)}
        tone={tone}
        to={tile.to}
        href={tile.href}
        large={large}
        badge={badge.count}
        badgeMax={badge.max}
        iconClass={tile.motion}
        label={badge.label}
      />
    );
  };

  return (
    <nav className="hub-menu flex flex-col gap-4" aria-label={ht.menu}>
      <ul className="hub-menu__heroes grid grid-cols-2 gap-2" aria-label={ht.groups.main}>
        <li className="min-w-0">{renderTile(SEARCH_TILE, 'hero', true)}</li>
        <li className="min-w-0">{renderTile(DAILY_TILE, 'hero', true)}</li>
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
            <ul className="grid grid-cols-2 gap-2 lg:grid-cols-4">
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
