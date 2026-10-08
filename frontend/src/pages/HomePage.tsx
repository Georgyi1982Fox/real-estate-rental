import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import type { ListingsPage } from '../api/types';
import CityPicker from '../components/CityPicker';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import HubMenu from '../components/HubMenu';
import ListingCard from '../components/ListingCard';
import SearchBar from '../components/SearchBar';
import Skeleton from '../components/Skeleton';
import { useApi } from '../hooks/useApi';
import { useCity } from '../hooks/useCity';
import { useCityDistricts, useDistricts } from '../hooks/useDistricts';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { fill } from '../lib/format';
import { FILTER_KEYS, QUERY_KEY } from '../lib/searchFilters';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';

const NEW_LISTINGS_COUNT = 6;
const SKELETON_COUNT = 3;
const GRID_CLASS = 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3';
const NO_DISTRICTS: string[] = [];

/** Параметры ленты: раньше она жила на «/», старые ссылки (?district=…&q=…) ведут в /search */
const SEARCH_PARAMS = [...FILTER_KEYS, QUERY_KEY, 'page'];

/** Главный экран-«хаб»: приветствие, поиск, меню всех разделов и новые объявления */
export default function HomePage() {
  const { t } = useI18n();
  const ht = t.hub;
  const { user } = useAuth();
  const { search } = useLocation();
  const navigate = useNavigate();
  const cities = useCity();
  const { city } = cities;
  // Названия — всех районов (карточки); в подсказках поиска — только районы выбранного города
  const { names } = useDistricts();
  const districts = useCityDistricts(city);
  const { data, error, loading, reload } = useApi<ListingsPage>(
    `/api/listings?page=1&per_page=${NEW_LISTINGS_COUNT}${city ? `&city=${encodeURIComponent(city)}` : ''}`,
    // «Назад» из объявления: список сразу на месте, прокрутка восстанавливается
    { remember: true },
  );

  useDocumentTitle(`bina.ai — ${ht.page_title}`);

  const params = new URLSearchParams(search);
  if (SEARCH_PARAMS.some((key) => params.has(key))) {
    return <Navigate to={`/search${search}`} replace />;
  }

  const name = user?.first_name.trim() ?? '';

  return (
    <section className="home flex flex-col gap-6" aria-labelledby="home-title">
      <header className="home__hero flex flex-col gap-4 pt-2 sm:pt-4">
        <h1 id="home-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
          {name ? fill(ht.greeting, name) : ht.greeting_guest}
        </h1>
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

      <section
        className="home__listings flex flex-col gap-4"
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
      </section>
    </section>
  );
}
