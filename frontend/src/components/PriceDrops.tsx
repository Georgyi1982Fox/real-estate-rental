import { Link } from 'react-router-dom';
import type { ListingsPage } from '../api/types';
import { useApi } from '../hooks/useApi';
import type { DistrictNames } from '../hooks/useDistricts';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import ListingCard from './ListingCard';

const PRICE_DROPS_LIMIT = 10;
/** «Все» — поиск с фильтром «📉 Только подешевевшие»; город поиск берёт сам (useCity) */
const PRICE_DROPS_SEARCH = '/search?price_dropped=true';
// Мобильный: горизонтальная лента со свайпом; от 640px — обычная сетка
const TRACK_CLASS =
  'price-drops__track no-scrollbar -mx-4 flex list-none snap-x snap-mandatory scroll-px-4 gap-4 overflow-x-auto px-4 pb-2 pt-1 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-x-visible sm:px-0 lg:grid-cols-3';
const ITEM_CLASS = 'price-drops__item w-[80%] max-w-xs shrink-0 snap-start sm:w-auto sm:max-w-none';

interface PriceDropsProps {
  districtNames: DistrictNames;
  /** Город ленты главной; пусто — вся Грузия */
  city?: string;
}

/**
 * «📉 Подешевели» на главной аренды (FRONTEND-055): до 10 квартир, подешевевших за 30 дней.
 * Таких нет (или не загрузилось) — блока нет, главная выглядит как раньше
 */
export default function PriceDrops({ districtNames, city }: PriceDropsProps) {
  const { t } = useI18n();
  const cityParam = city ? `&city=${encodeURIComponent(city)}` : '';
  const { data } = useApi<ListingsPage>(
    `/api/listings?price_dropped=true&per_page=${PRICE_DROPS_LIMIT}${cityParam}`,
    // «Назад» из квартиры: лента сразу на месте, затем тихо обновляется
    { remember: true },
  );
  const items = data?.items ?? [];

  if (items.length === 0) return null;

  return (
    <section className="price-drops flex flex-col gap-4" aria-labelledby="price-drops-title">
      <header className="flex items-baseline justify-between gap-3">
        <h2 id="price-drops-title" className="text-xl font-bold tracking-tight">
          <span aria-hidden="true">📉 </span>
          {t.price_drop.home_title}
        </h2>
        <Link
          to={PRICE_DROPS_SEARCH}
          className="price-drops__all rounded-[var(--radius-sm)] text-sm font-semibold text-[var(--text-primary)] underline underline-offset-2 hover:text-[var(--text-secondary)]"
          onClick={() => haptic('light')}
        >
          {t.hub.see_all}
        </Link>
      </header>
      <ul className={TRACK_CLASS}>
        {items.map((listing) => (
          <li key={listing.id} className={ITEM_CLASS}>
            <ListingCard listing={listing} districtNames={districtNames} headingLevel="h3" />
          </li>
        ))}
      </ul>
    </section>
  );
}
