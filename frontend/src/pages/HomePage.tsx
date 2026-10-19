import { useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import type { ListingsPage } from '../api/types';
import CityPicker from '../components/CityPicker';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import HubMenu from '../components/HubMenu';
import ListingCard from '../components/ListingCard';
import Pagination from '../components/Pagination';
import Recommendations from '../components/Recommendations';
import RecentlyViewed from '../components/RecentlyViewed';
import SearchBar from '../components/SearchBar';
import Skeleton from '../components/Skeleton';
import { useApi } from '../hooks/useApi';
import { useCity } from '../hooks/useCity';
import { useCityDistricts, useDistricts } from '../hooks/useDistricts';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { useUrlParams } from '../hooks/useUrlParams';
import { fill } from '../lib/format';
import { QUERY_KEY } from '../lib/searchFilters';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';

/** Новых объявлений на странице: три ряда по три на компьютере, недолго листать на телефоне */
const NEW_LISTINGS_PER_PAGE = 9;
const SKELETON_COUNT = 3;
const GRID_CLASS = 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3';
const NO_DISTRICTS: string[] = [];

/** Номер страницы новых объявлений из ?page= (неверный — первая) */
function pageFrom(search: string): number {
  const value = Number(new URLSearchParams(search).get('page'));
  return Number.isInteger(value) && value > 1 ? value : 1;
}

/**
 * Главная аренды (второй экран после выбора «Аренда»): поиск, меню поиска, «Вы смотрели»,
 * «Вам может понравиться» и новые объявления по страницам 1 2 3 4 5
 */
export default function HomePage() {
  const { t } = useI18n();
  const ht = t.hub;
  const { user } = useAuth();
  const navigate = useNavigate();
  const { search, update } = useUrlParams();
  const page = pageFrom(search);
  const listingsRef = useRef<HTMLElement>(null);
  const cities = useCity();
  const { city } = cities;
  // Названия — всех районов (карточки); в подсказках поиска — только районы выбранного города
  const { names } = useDistricts();
  const districts = useCityDistricts(city);
  const { data, error, loading, reload } = useApi<ListingsPage>(
    `/api/listings?page=${page}&per_page=${NEW_LISTINGS_PER_PAGE}${city ? `&city=${encodeURIComponent(city)}` : ''}`,
    // «Назад» из объявления: список сразу на месте, прокрутка восстанавливается
    { remember: true },
  );

  useDocumentTitle(`bina.ai — ${t.start.rent.title}`);
  useTelegramBackButton('/');

  const name = user?.first_name.trim() ?? '';

  const changePage = (next: number) => {
    update((params) => {
      if (next > 1) params.set('page', String(next));
      else params.delete('page');
    }, false, true);
    listingsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <section className="home flex flex-col gap-6" aria-labelledby="home-title">
      <header className="home__hero flex flex-col gap-4 pt-2 sm:pt-4">
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium text-[var(--text-secondary)]">
            {name ? fill(ht.greeting, name) : ht.greeting_guest}
          </p>
          <h1 id="home-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
            {t.start.rent.title}
          </h1>
        </div>
        <CityPicker
          city={city}
          cities={cities.cities}
          loading={cities.loading}
          failed={cities.error !== undefined}
          onRetry={cities.reload}
          onChange={cities.setCity}
        />
        {/* Поиск с главной открывает ленту /search с этим запросом или районом */}
        <SearchBar
          query=""
          districts={districts}
          selectedDistricts={NO_DISTRICTS}
          onSearch={(text) => {
            if (text) navigate(`/search?${new URLSearchParams({ [QUERY_KEY]: text })}`);
          }}
          onSelectDistrict={(id) => navigate(`/search?${new URLSearchParams({ district: id })}`)}
        />
      </header>

      <HubMenu />

      <RecentlyViewed districtNames={names} />

      <Recommendations districtNames={names} quiet />

      <section
        ref={listingsRef}
        className="home__listings flex scroll-mt-4 flex-col gap-4"
        aria-labelledby="home-listings-title"
        aria-busy={loading}
      >
        <header className="flex items-baseline justify-between gap-3">
          <h2 id="home-listings-title" className="text-xl font-bold tracking-tight">
            {ht.new_listings}
          </h2>
          <Link
            to="/search"
            className="home__see-all rounded-[var(--radius-sm)] text-sm font-semibold text-[var(--text-primary)] underline underline-offset-2 hover:text-[var(--text-secondary)]"
          >
            {ht.see_all}
          </Link>
        </header>

        {loading && (
          <div className={GRID_CLASS}>
            {Array.from({ length: SKELETON_COUNT }, (_, index) => (
              <Skeleton key={index} />
            ))}
          </div>
        )}

        {error && <ErrorState onRetry={reload} />}

        {data && data.items.length === 0 && (
          <EmptyState title={t.home.empty_title} text={t.home.empty_text} />
        )}

        {data && data.items.length > 0 && (
          <div className={GRID_CLASS}>
            {data.items.map((listing) => (
              <ListingCard
                key={listing.id}
                listing={listing}
                districtNames={names}
                headingLevel="h3"
              />
            ))}
          </div>
        )}

        {/* Страницы 1 2 3 4 5: листать новые объявления, не уходя в поиск */}
        {data && data.pages > 1 && (
          <Pagination current={data.page} total={data.pages} onChange={changePage} />
        )}
      </section>
    </section>
  );
}
