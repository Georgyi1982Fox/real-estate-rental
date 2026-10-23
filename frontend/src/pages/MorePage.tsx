import { useCallback, useId, useState } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import ExternalLink from '../components/ExternalLink';
import Icon from '../components/Icon';
import type { IconName } from '../components/Icon';
import Modal from '../components/Modal';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useSubscription } from '../hooks/useSubscription';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import type { Strings } from '../i18n/strings';
import { ACCEPTANCE_PATH } from '../lib/acceptance';
import { botSectionUrl } from '../lib/config';
import { fill, formatDate } from '../lib/format';
import { MY_HOTELS_PATH } from '../lib/hotels';
import { INVITE_PATH } from '../lib/referral';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

type GroupKey = keyof Strings['more']['groups'];

/**
 * Цвет квадратика иконки (--tone-* из theme.css). Иконка — цветом фона карточки:
 * белая на пастели в светлой теме и тёмная на светлой пастели в тёмной
 */
type Tone = 'search' | 'owner' | 'benefit' | 'housing' | 'more' | 'hero';

const TONE_BG: Record<Tone, string> = {
  search: 'bg-[var(--tone-search)]',
  owner: 'bg-[var(--tone-owner)]',
  benefit: 'bg-[var(--tone-benefit)]',
  housing: 'bg-[var(--tone-housing)]',
  more: 'bg-[var(--tone-more)]',
  hero: 'bg-[var(--tone-hero)]',
};

interface Row {
  key: string;
  icon: IconName;
  tone: Tone;
  title: string;
  text: string;
  /** Страница приложения */
  to?: string;
  /** Раздел бота */
  href?: string;
  /** Кнопка (окно «О приложении») */
  onClick?: () => void;
}

const ROW_CLASS =
  'more-row flex min-h-16 w-full items-center gap-3 px-4 py-3 text-left hover:bg-[var(--surface-hover)] active:bg-[var(--surface-hover)]';

function RowContent({ row, inBot }: { row: Row; inBot: string }) {
  return (
    <>
      <span
        className={`more-row__icon inline-grid size-10 shrink-0 place-items-center rounded-xl text-[var(--surface)] shadow-[var(--shadow-sm)] ${TONE_BG[row.tone]}`}
      >
        <Icon name={row.icon} className="size-5" />
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="more-row__title text-sm font-semibold leading-tight">{row.title}</span>
        <span className="more-row__text truncate text-xs leading-snug text-[var(--text-secondary)]">
          {row.text}
        </span>
      </span>
      {row.href ? (
        // Раздел работает в боте — подпись, чтобы переход в чат не был неожиданным
        <span className="more-row__bot inline-flex shrink-0 items-center gap-1 text-xs text-[var(--text-secondary)]">
          {inBot}
          <Icon name="external" className="size-3.5" />
        </span>
      ) : (
        <Icon name="chevron" className="size-4 shrink-0 text-[var(--text-secondary)]" />
      )}
    </>
  );
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  const titleId = useId();
  return (
    <section className="more-group flex flex-col gap-2" aria-labelledby={titleId}>
      <h2
        id={titleId}
        className="px-1 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]"
      >
        {title}
      </h2>
      <ul className="more-group__list divide-y divide-[var(--border)] overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)]">
        {children}
      </ul>
    </section>
  );
}

/** «Ещё»: Premium и друг сверху, ниже — размещение, инструменты, помощь и документы сервиса */
export default function MorePage() {
  const { lang, t } = useI18n();
  const mt = t.more;
  const tiles = t.hub.tiles;
  const { subscription } = useSubscription();
  const [aboutOpen, setAboutOpen] = useState(false);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeAbout = useCallback(() => setAboutOpen(false), []);

  useDocumentTitle(`${mt.page_title} — bina.ai`);
  useTelegramBackButton('/');

  const premiumUntil =
    subscription?.is_premium && subscription.expires_at
      ? formatDate(subscription.expires_at, lang)
      : '';

  const groups: { key: GroupKey; rows: Row[] }[] = [
    {
      key: 'owners',
      rows: [
        { key: 'owner', icon: 'home_plus', tone: 'owner', ...tiles.owner, to: '/my-listings' },
        { key: 'my_hotels', icon: 'hotel', tone: 'owner', ...tiles.my_hotels, to: MY_HOTELS_PATH },
      ],
    },
    {
      key: 'tools',
      rows: [
        {
          key: 'acceptance',
          icon: 'list_checks',
          tone: 'search',
          ...mt.acceptance,
          to: ACCEPTANCE_PATH,
        },
        { key: 'rent', icon: 'calendar', tone: 'housing', ...tiles.rent, href: botSectionUrl('rent') },
      ],
    },
    {
      key: 'help',
      rows: [
        { key: 'help', icon: 'help', tone: 'hero', ...tiles.help, to: '/help' },
        {
          key: 'support',
          icon: 'message',
          tone: 'hero',
          ...tiles.support,
          href: botSectionUrl('support'),
        },
        {
          key: 'about',
          icon: 'info',
          tone: 'more',
          ...mt.about,
          onClick: () => setAboutOpen(true),
        },
      ],
    },
    {
      key: 'legal',
      rows: [
        { key: 'terms', icon: 'file', tone: 'more', ...tiles.terms, to: '/legal/terms' },
        { key: 'privacy', icon: 'lock', tone: 'more', ...tiles.privacy, to: '/legal/privacy' },
      ],
    },
  ];

  const renderRow = (row: Row) => {
    const content = <RowContent row={row} inBot={mt.in_bot} />;
    if (row.href) {
      return (
        <ExternalLink href={row.href} className={ROW_CLASS}>
          {content}
        </ExternalLink>
      );
    }
    if (row.onClick) {
      const onClick = row.onClick;
      return (
        <button
          type="button"
          className={ROW_CLASS}
          aria-haspopup="dialog"
          onClick={() => {
            haptic('light');
            onClick();
          }}
        >
          {content}
        </button>
      );
    }
    return (
      <Link to={row.to ?? '/'} className={ROW_CLASS} onClick={() => haptic('light')}>
        {content}
      </Link>
    );
  };

  return (
    <section
      className="more mx-auto flex w-full max-w-2xl flex-col gap-6 py-2 sm:py-4"
      aria-labelledby="more-title"
    >
      <header className="flex flex-col gap-1">
        <h1 id="more-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
          {mt.page_title}
        </h1>
        <p className="text-sm text-[var(--text-secondary)]">{mt.subtitle}</p>
      </header>

      <div className="more__highlights grid grid-cols-1 gap-3 sm:grid-cols-2">
        {/* Premium — главный баннер раздела */}
        <Link
          to="/premium"
          className="more-premium group relative flex min-h-36 flex-col justify-between gap-3 overflow-hidden rounded-[var(--radius-lg)] bg-linear-135 from-[var(--premium-from)] to-[var(--premium-to)] p-5 text-[var(--premium-ink)] shadow-[var(--shadow-md)] hover:shadow-[var(--shadow-lg)] active:scale-[.98]"
          onClick={() => haptic('light')}
        >
          <Icon
            name="crown"
            className="pointer-events-none absolute -right-3 -bottom-4 size-28 stroke-[1.2] opacity-20"
          />
          <span className="flex items-center gap-2">
            <span className="inline-grid size-10 place-items-center rounded-xl bg-white/40">
              <Icon name="crown" className="size-5" />
            </span>
            <span className="text-lg font-bold tracking-tight">{tiles.premium.title}</span>
          </span>
          <span className="relative text-sm font-medium leading-snug">
            {premiumUntil ? fill(mt.premium_active, premiumUntil) : mt.premium_text}
          </span>
          <span className="relative inline-flex items-center gap-1 self-start rounded-full bg-[var(--premium-ink)] px-3 py-1.5 text-xs font-semibold text-white">
            {premiumUntil ? mt.premium_manage : mt.premium_open}
            <Icon name="arrow_right" className="size-3.5" />
          </span>
        </Link>

        {/* Пригласить друга — второй баннер, компактный */}
        <Link
          to={INVITE_PATH}
          className="more-invite group relative flex items-center gap-3 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[var(--shadow-sm)] hover:bg-[var(--surface-hover)] active:scale-[.98] sm:flex-col sm:items-start sm:justify-between sm:p-5"
          onClick={() => haptic('light')}
        >
          <Icon
            name="gift"
            className="pointer-events-none absolute -right-3 -bottom-4 hidden size-24 stroke-[1.2] text-[var(--tone-benefit)] opacity-20 sm:block"
          />
          <span className="inline-grid size-10 shrink-0 place-items-center rounded-xl bg-[var(--tone-benefit)] text-[var(--surface)]">
            <Icon name="gift" className="size-5" />
          </span>
          <span className="relative flex min-w-0 flex-1 flex-col sm:flex-none">
            <span className="text-base font-bold tracking-tight">{tiles.invite.title}</span>
            <span className="text-sm leading-snug text-[var(--text-secondary)]">
              {tiles.invite.text}
            </span>
          </span>
          <Icon name="chevron" className="relative size-4 shrink-0 text-[var(--text-secondary)] sm:hidden" />
        </Link>
      </div>

      {groups.map((group) => (
        <Group key={group.key} title={mt.groups[group.key]}>
          {group.rows.map((row) => (
            <li key={row.key}>{renderRow(row)}</li>
          ))}
        </Group>
      ))}

      <Modal open={aboutOpen} title={mt.about.title} onClose={closeAbout}>
        <p className="text-sm leading-relaxed">{t.profile.about_text}</p>
        <p className="mt-4 text-xs text-[var(--text-secondary)]">
          © {new Date().getFullYear()} bina.ai
        </p>
      </Modal>
    </section>
  );
}
