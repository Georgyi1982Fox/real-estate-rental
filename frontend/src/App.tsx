import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';
import Layout from './components/Layout';
import { ACCEPTANCE_PATH } from './lib/acceptance';
import { AGENCY_PATH } from './lib/agency';
import { COMPARE_PATH } from './lib/compare';
import { HISTORY_PATH } from './lib/history';
import { INVITE_PATH } from './lib/referral';
import { HOTELS_PATH, MY_HOTELS_PATH, NEW_HOTEL_PATH } from './lib/hotels';
import { MY_LISTINGS_PATH, NEW_LISTING_PATH } from './lib/ownerListings';
import { MORE_PATH, RENT_PATH } from './lib/paths';
import { DAILY_SEARCH_PATH, SMART_SORT, SORT_KEY } from './lib/searchFilters';
import { DOCUMENTS_PATH } from './lib/signing';
import AcceptancePage from './pages/AcceptancePage';
import AgencyCabinetPage from './pages/AgencyCabinetPage';
import AgencyPage from './pages/AgencyPage';
import AuthPage from './pages/AuthPage';
import ComparePage from './pages/ComparePage';
import FavoritesPage from './pages/FavoritesPage';
import FeatureLabPage from './pages/FeatureLabPage';
import HelpPage from './pages/HelpPage';
import HistoryPage from './pages/HistoryPage';
import HomePage from './pages/HomePage';
import HotelFormPage from './pages/HotelFormPage';
import HotelPage from './pages/HotelPage';
import HotelsPage from './pages/HotelsPage';
import LegalPage from './pages/LegalPage';
import MyDocumentsPage from './pages/MyDocumentsPage';
import MyHotelsPage from './pages/MyHotelsPage';
import MyListingsPage from './pages/MyListingsPage';
import ListingFormPage from './pages/ListingFormPage';
import ListingPage from './pages/ListingPage';
import MorePage from './pages/MorePage';
import NotFoundPage from './pages/NotFoundPage';
import NotificationsPage from './pages/NotificationsPage';
import PremiumPage from './pages/PremiumPage';
import ProfilePage from './pages/ProfilePage';
import SavedSearchesPage from './pages/SavedSearchesPage';
import SearchPage from './pages/SearchPage';
import InvitePage from './pages/InvitePage';
import StartPage from './pages/StartPage';
import TestCardPage from './pages/TestCardPage';
import { AuthProvider } from './providers/AuthProvider';
import { I18nProvider } from './providers/I18nProvider';
import { ToastProvider } from './providers/ToastProvider';

const router = createBrowserRouter(
  [
    {
      element: <Layout />,
      children: [
        // Стартовый экран: аренда, продажа (скоро), гостиницы. Ссылки на объект или раздел
        // (из бота, «Поделиться») ведут сразу туда, минуя его
        { path: '/', element: <StartPage /> },
        { path: RENT_PATH, element: <HomePage /> },
        { path: MORE_PATH, element: <MorePage /> },
        { path: '/search', element: <SearchPage /> },
        { path: '/listing/:id', element: <ListingPage /> },
        // Сравнение 2-3 квартир (FRONTEND-027): «⚖ Сравнить» в поиске и избранном
        { path: COMPARE_PATH, element: <ComparePage /> },
        // Гостиницы (FRONTEND-045): отдельный раздел, с квартирами не смешивается
        { path: HOTELS_PATH, element: <HotelsPage /> },
        { path: `${HOTELS_PATH}/:id`, element: <HotelPage /> },
        { path: MY_HOTELS_PATH, element: <MyHotelsPage /> },
        // key: «Разместить» и «Изменить» — разные формы, состояние не переносится
        { path: NEW_HOTEL_PATH, element: <HotelFormPage key="new" /> },
        { path: `${MY_HOTELS_PATH}/:id/edit`, element: <HotelFormPage key="edit" /> },
        // Акт приёмки квартиры (FRONTEND-024): из объявления (?listing=) и из профиля
        { path: ACCEPTANCE_PATH, element: <AcceptancePage /> },
        // «Мои документы» — отправленные на подпись (FRONTEND-042), вход из профиля
        { path: DOCUMENTS_PATH, element: <MyDocumentsPage /> },
        { path: '/help', element: <HelpPage /> },
        { path: '/legal/:doc', element: <LegalPage /> },
        // Посуточная аренда — та же лента в режиме «Посуточно»
        { path: '/daily', element: <Navigate to={DAILY_SEARCH_PATH} replace /> },
        // Умный поиск — режим «По смыслу» в общей ленте (FRONTEND-031)
        { path: '/smart', element: <Navigate to={`/search?${SORT_KEY}=${SMART_SORT}`} replace /> },
        // «Сдать квартиру» (FRONTEND-033): вкладка «Сдать» и «Ещё» → «Разместить объект»
        { path: MY_LISTINGS_PATH, element: <MyListingsPage /> },
        { path: NEW_LISTING_PATH, element: <ListingFormPage /> },
        // Кабинет риелтора (FRONTEND-038) и страница агентства — она открывается и без входа
        { path: AGENCY_PATH, element: <AgencyCabinetPage /> },
        { path: `${AGENCY_PATH}/:id`, element: <AgencyPage /> },
        { path: '/favorites', element: <FavoritesPage /> },
        { path: HISTORY_PATH, element: <HistoryPage /> },
        // «Пригласить друга» (FRONTEND-029): из профиля и «Ещё»
        { path: INVITE_PATH, element: <InvitePage /> },
        { path: '/profile', element: <ProfilePage /> },
        { path: '/premium', element: <PremiumPage /> },
        { path: '/searches', element: <SavedSearchesPage /> },
        { path: '/notifications', element: <NotificationsPage /> },
        { path: '/test_card', element: <TestCardPage /> },
        // Временная «Проверка функций» для владельца (удалить после FRONTEND-023…029)
        { path: '/lab', element: <FeatureLabPage /> },
        { path: '*', element: <NotFoundPage /> },
      ],
    },
    // Экран входа — без шапки и подвала
    { path: '/auth', element: <AuthPage /> },
  ],
  {
    // '/real-estate-rental' на GitHub Pages, '/' в dev (см. base в vite.config.ts)
    basename: import.meta.env.BASE_URL.replace(/\/+$/, '') || '/',
  },
);

// AuthProvider выше роутера, поэтому после выхода навигация — напрямую через router
const goToAuth = () => {
  void router.navigate('/auth', { replace: true });
};

export default function App() {
  return (
    <I18nProvider>
      <AuthProvider onLogout={goToAuth}>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </AuthProvider>
    </I18nProvider>
  );
}
