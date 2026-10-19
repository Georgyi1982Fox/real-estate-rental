import { Link, Navigate, useLocation } from 'react-router-dom';
import Icon from '../components/Icon';
import type { IconName } from '../components/Icon';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import type { Strings } from '../i18n/strings';
import { fill } from '../lib/format';
import { HOTELS_PATH } from '../lib/hotels';
import { RENT_PATH } from '../lib/paths';
import { FILTER_KEYS, QUERY_KEY } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

type DirectionKey = keyof Pick<Strings['start'], 'rent' | 'sale' | 'hotels'>;

interface Direction {
  key: DirectionKey;
  icon: IconName;
  /** Раздел приложения; без него — направление ещё закрыто («Скоро») */
  to?: string;
  /** Класс фона карточки (градиент из theme.css) */
  tone?: string;
}

// Порядок — как решил владелец: аренда, продажа (скоро), гостиницы
const DIRECTIONS: Direction[] = [
  {
    key: 'rent',
    icon: 'key',
    to: RENT_PATH,
    tone: 'bg-linear-135 from-[var(--direction-rent-from)] to-[var(--direction-rent-to)]',
  },
  { key: 'sale', icon: 'building' },
  {
    key: 'hotels',
    icon: 'hotel',
    to: HOTELS_PATH,
    tone: 'bg-linear-135 from-[var(--direction-hotels-from)] to-[var(--direction-hotels-to)]',
  },
];

/**
 * Старые ссылки на ленту жили на «/» (?district=…&q=…, кнопка бота «Открыть с этим поиском»):
 * они ведут сразу в поиск, минуя выбор направления
 */
const SEARCH_PARAMS = [...FILTER_KEYS, QUERY_KEY, 'page'];

const CARD_CLASS =
  'start-card group relative flex min-h-32 w-full items-center gap-4 overflow-hidden rounded-[var(--radius-lg)] p-5 text-left shadow-[var(--shadow-md)] sm:min-h-44 sm:flex-col sm:items-start sm:justify-between';

/** Стартовый экран: три направления — аренда, продажа (скоро) и гостиницы */
export default function StartPage() {
  const { t } = useI18n();
  const st = t.start;
  const { user } = useAuth();
  const { search } = useLocation();
  const showToast = useToast();

  useDocumentTitle(`bina.ai — ${st.page_title}`);

  const params = new URLSearchParams(search);
  if (SEARCH_PARAMS.some((key) => params.has(key))) {
    return <Navigate to={`/search${search}`} replace />;
  }

  const name = user?.first_name.trim() ?? '';

  const content = (direction: Direction, locked: boolean) => (
    <>
      {/* Большая иконка-«водяной знак» в углу карточки */}
      <Icon
        name={direction.icon}
        className={`start-card__watermark pointer-events-none absolute -right-5 -bottom-12 size-32 stroke-[1.2] ${
          locked ? 'text-[var(--text-secondary)] opacity-10' : 'text-white opacity-15'
        }`}
      />
      <span
        className={`start-card__icon inline-grid size-14 shrink-0 place-items-center rounded-2xl ${
          locked
            ? 'bg-[var(--surface-hover)] text-[var(--text-secondary)]'
            : 'bg-[var(--direction-glow)] text-white ring-1 ring-white/25'
        }`}
      >
        <Icon name={direction.icon} className="size-7 stroke-[1.75]" />
      </span>
      <span className="start-card__body relative flex min-w-0 flex-1 flex-col gap-1 sm:flex-none">
        <span className="flex items-center gap-2">
          <span className="start-card__title text-xl font-bold tracking-tight sm:text-2xl">
            {st[direction.key].title}
          </span>
          {locked && (
            <span className="start-card__soon inline-flex items-center gap-1 rounded-full bg-[var(--warning-bg)] px-2.5 py-0.5 text-xs font-semibold text-[var(--warning-text)]">
              <Icon name="lock" className="size-3" />
              {t.soon.badge}
            </span>
          )}
        </span>
        <span
          className={`start-card__text text-sm leading-snug ${
            locked ? 'text-[var(--text-secondary)]' : 'text-white/90'
          }`}
        >
          {st[direction.key].text}
        </span>
      </span>
      {!locked && (
        <span className="start-card__go relative inline-grid size-10 shrink-0 place-items-center rounded-full bg-white/20 text-white transition-transform duration-200 group-hover:translate-x-1 sm:self-end">
          <Icon name="arrow_right" className="size-5" />
        </span>
      )}
    </>
  );

  return (
    <section
      className="start mx-auto flex w-full max-w-3xl flex-col gap-6 py-2 sm:py-6"
      aria-labelledby="start-title"
    >
      <header className="start__hero flex flex-col gap-2">
        <p className="text-sm font-medium text-[var(--text-secondary)]">
          {name ? fill(st.greeting, name) : st.greeting_guest}
        </p>
        <h1 id="start-title" className="text-3xl font-bold tracking-tight sm:text-4xl">
          {st.question}
        </h1>
        <p className="max-w-xl text-sm leading-relaxed text-[var(--text-secondary)]">
          {st.subtitle}
        </p>
      </header>

      <ul className="start__directions grid grid-cols-1 gap-3 sm:grid-cols-3" aria-label={st.directions}>
        {DIRECTIONS.map((direction) => (
          <li key={direction.key} className="min-w-0">
            {direction.to ? (
              <Link
                to={direction.to}
                className={`${CARD_CLASS} ${direction.tone ?? ''} text-white hover:shadow-[var(--shadow-lg)] active:scale-[.98]`}
                onClick={() => haptic('light')}
              >
                {content(direction, false)}
              </Link>
            ) : (
              // Закрытое направление: карточка видна, нажатие — подсказка «скоро откроется»
              <button
                type="button"
                className={`${CARD_CLASS} start-card--locked border border-dashed border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] active:scale-[.99]`}
                aria-disabled="true"
                onClick={() => {
                  haptic('warning');
                  showToast(st.sale_soon);
                }}
              >
                {content(direction, true)}
              </button>
            )}
          </li>
        ))}
      </ul>

      <p className="start__trust flex items-start gap-2 text-xs leading-relaxed text-[var(--text-secondary)]">
        <Icon name="shield" className="mt-0.5 size-4 shrink-0 text-[var(--primary)]" />
        {st.trust}
      </p>
    </section>
  );
}
