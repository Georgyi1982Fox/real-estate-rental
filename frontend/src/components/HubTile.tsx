import { Link } from 'react-router-dom';
import { haptic } from '../lib/telegram';
import CountBadge from './CountBadge';
import ExternalLink from './ExternalLink';
import Icon from './Icon';
import type { IconName } from './Icon';

/**
 * Цвет иконки (--tone-* в theme.css): свой у каждой группы плиток,
 * hero — у двух больших плиток сверху
 */
export type HubTone = 'hero' | 'search' | 'owner' | 'benefit' | 'housing' | 'more';

const TONE_CLASS: Record<HubTone, string> = {
  hero: 'text-[var(--tone-hero)]',
  search: 'text-[var(--tone-search)]',
  owner: 'text-[var(--tone-owner)]',
  benefit: 'text-[var(--tone-benefit)]',
  housing: 'text-[var(--tone-housing)]',
  more: 'text-[var(--tone-more)]',
};

// Плитка без своего фона и рамки: тот же цвет, что у страницы, окрашена только иконка
const TILE_CLASS =
  'hub-tile flex h-full min-w-0 flex-col items-center gap-1.5 rounded-[var(--radius-lg)] px-2 py-3 text-center hover:bg-[var(--surface-hover)] active:scale-[.97]';

interface HubTileProps {
  icon: IconName;
  title: string;
  text: string;
  tone: HubTone;
  /** Страница приложения */
  to?: string;
  /** Внешняя ссылка (раздел бота): в Telegram открывается через SDK, в браузере — новой вкладкой */
  href?: string;
  /** Счётчик в углу иконки; 0 не показывается */
  badge?: number;
  /** Больше этого числа счётчик показывает «N+» */
  badgeMax?: number;
  /** Класс анимации иконки (например, .bell-ring у колокольчика с непрочитанными) */
  iconClass?: string;
  /** Имя ссылки для скринридера, если его нужно дополнить (например, числом непрочитанных) */
  label?: string;
  /** Крупная плитка-«герой» */
  large?: boolean;
}

/** Плитка главного меню: иконка, название, короткая подпись */
export default function HubTile({
  icon,
  title,
  text,
  tone,
  to,
  href,
  badge = 0,
  badgeMax = 9,
  iconClass = '',
  label,
  large = false,
}: HubTileProps) {
  const content = (
    <>
      <span className={`hub-tile__icon relative ${TONE_CLASS[tone]}`}>
        <Icon name={icon} className={`stroke-[1.5] ${large ? 'size-12' : 'size-9'} ${iconClass}`} />
        <CountBadge count={badge} max={badgeMax} />
      </span>
      <span
        className={`hub-tile__title font-semibold leading-tight ${large ? 'text-base' : 'text-sm'}`}
      >
        {title}
      </span>
      <span className="hub-tile__text text-xs leading-snug text-[var(--text-secondary)]">
        {text}
      </span>
    </>
  );

  if (href) {
    return (
      <ExternalLink href={href} className={TILE_CLASS}>
        {content}
      </ExternalLink>
    );
  }

  return (
    <Link to={to ?? '/'} className={TILE_CLASS} aria-label={label} onClick={() => haptic('light')}>
      {content}
    </Link>
  );
}
