import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import type { HotelsPage as HotelsResponse } from '../api/types';
import ChipList from '../components/ChipList';
import CityPicker from '../components/CityPicker';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import FilterButton from '../components/FilterButton';
import HotelCard from '../components/HotelCard';
import HotelFilterModal from '../components/HotelFilterModal';
import HotelSortSelect from '../components/HotelSortSelect';
import Icon from '../components/Icon';
import Pagination from '../components/Pagination';
import Skeleton from '../components/Skeleton';
import { useApi } from '../hooks/useApi';
import { useCity } from '../hooks/useCity';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useHotelFilters } from '../hooks/useHotelFilters';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { plural } from '../lib/format';
import {
  countHotelFilters,
  hasHotelFilters,
  hotelFilterChips,
  hotelsQuery,
} from '../lib/hotelFilters';
import { NEW_HOTEL_PATH } from '../lib/hotels';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

const HOTELS_PER_PAGE = 6;
const SKELETON_COUNT = 4;
const GRID_CLASS = 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';
const PRIMARY_BUTTON_CLASS =
  'inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]';

/** Поиск гостиниц: город из общего выбора, фильтры, сортировка и страницы */
export default function HotelsPage() {
  const { lang, t } = useI18n();
  const ht = t.hotels;
  const { filters, sort, page, setFilters, replaceFilters, resetFilters, setSort, setPage } =
    useHotelFilters();
  const [filtersOpen, setFiltersOpen] = useState(false);
  const openFilters = useCallback(() => setFiltersOpen(true), []);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeFilters = useCallback(() => setFiltersOpen(false), []);
  const cities = useCity();
  const { city } = cities;
  const query = hotelsQuery(filters, city, sort);
  // remember: «Назад» из гостиницы сразу показывает тот же список на той же прокрутке
  const { data, error, loading, reload } = useApi<HotelsResponse>(
    `/api/hotels?page=${page}&per_page=${HOTELS_PER_PAGE}${query ? `&${query}` : ''}`,
    { remember: true },
  );
  const filtered = hasHotelFilters(filters);

  useDocumentTitle(`${ht.page_title} — bina.ai`);
  useTelegramBackButton('/');

  const changeCity = (next: string | undefined) => {
    cities.setCity(next);
    // В другом городе страниц может быть меньше
    if (page > 1) setPage(1);
  };

  const changePage = (next: number) => {
    setPage(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const reset = () => {
    haptic('light');
    resetFilters();
  };

  let heading = filtered ? ht.results : ht.all;
  if (data && data.total > 0) heading = plural(filtered ? ht.found : ht.count, data.total, lang);

  return (
    <section className="hotels-page space-y-6" aria-labelledby="hotels-title">
      <header className="hotels-page__header space-y-2 py-2 sm:py-4">
        <h1 id="hotels-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
          {ht.page_title}
        </h1>
        <p className="m-0 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
          {ht.intro}
        </p>
      </header>

      <section className="hotels-page__filters flex flex-col gap-4" aria-label={t.home.filters}>
        <div className="hotels-page__modes flex flex-wrap items-center gap-2">
          <CityPicker
            city={city}
            cities={cities.cities}
            loading={cities.loading}
            failed={cities.error !== undefined}
            onRetry={cities.reload}
            onChange={changeCity}
          />
          <FilterButton count={countHotelFilters(filters)} onClick={openFilters} />
        </div>
        <ChipList
          chips={hotelFilterChips(filters, t, lang)}
          onRemove={setFilters}
          onEdit={openFilters}
        />
        {filtered && (
          <button
            type="button"
            className="hotels-page__reset inline-flex min-h-11 items-center justify-center gap-2 self-start rounded-[var(--radius-md)] px-3 py-2.5 text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] active:scale-[.98]"
            onClick={reset}
          >
            <Icon name="close" className="size-4" />
            {t.home.reset_filters}
          </button>
        )}
        <HotelFilterModal
          open={filtersOpen}
          onClose={closeFilters}
          filters={filters}
          city={city}
          onApply={replaceFilters}
        />
      </section>

      <section
        className="hotels-page__list space-y-6"
        aria-labelledby="hotels-list-title"
        aria-busy={loading}
      >
        <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2
            id="hotels-list-title"
            className="min-w-0 break-words text-xl font-bold tracking-tight"
            aria-live="polite"
          >
            {heading}
          </h2>
          <HotelSortSelect value={sort} onChange={setSort} />
        </header>

        {loading && (
          <div className={GRID_CLASS}>
            {Array.from({ length: SKELETON_COUNT }, (_, index) => (
              <Skeleton key={index} />
            ))}
          </div>
        )}

        {error && <ErrorState onRetry={reload} />}

        {data && data.items.length === 0 && filtered && (
          <EmptyState icon="🔍" title={ht.empty_filtered_title} text={ht.empty_filtered_text}>
            <button type="button" className={PRIMARY_BUTTON_CLASS} onClick={reset}>
              {t.home.reset_filters}
            </button>
          </EmptyState>
        )}

        {data && data.items.length === 0 && !filtered && (
          <EmptyState icon="🏨" title={ht.empty_title} text={ht.empty_text}>
            <Link to={NEW_HOTEL_PATH} className={PRIMARY_BUTTON_CLASS} onClick={() => haptic('light')}>
              {ht.add}
            </Link>
          </EmptyState>
        )}

        {data && data.items.length > 0 && (
          <>
            <div className={GRID_CLASS}>
              {data.items.map((hotel) => (
                <HotelCard key={hotel.id} hotel={hotel} cityNames={cities.names} headingLevel="h3" />
              ))}
            </div>
            <Pagination current={data.page} total={data.pages} onChange={changePage} />
          </>
        )}
      </section>

      {/* Хозяину: размещение — внизу ленты, чтобы не спорить с поиском */}
      {data && data.items.length > 0 && (
        <aside className="hotels-page__owner flex flex-col items-start gap-3 rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] p-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="m-0 text-sm text-[var(--text-secondary)]">{ht.empty_text}</p>
          <Link
            to={NEW_HOTEL_PATH}
            className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-2.5 text-sm font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-hover)] active:scale-[.98]"
            onClick={() => haptic('light')}
          >
            <Icon name="hotel" className="size-4" />
            {ht.add}
          </Link>
        </aside>
      )}
    </section>
  );
}
