import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';
import Layout from './components/Layout';
import { HOTELS_PATH, MY_HOTELS_PATH, NEW_HOTEL_PATH } from './lib/hotels';
import { DAILY_SEARCH_PATH } from './lib/searchFilters';
import AuthPage from './pages/AuthPage';
import FavoritesPage from './pages/FavoritesPage';
import FeatureLabPage from './pages/FeatureLabPage';
import HelpPage from './pages/HelpPage';
import HomePage from './pages/HomePage';
import HotelFormPage from './pages/HotelFormPage';
import HotelPage from './pages/HotelPage';
import HotelsPage from './pages/HotelsPage';
import LegalPage from './pages/LegalPage';
import MyHotelsPage from './pages/MyHotelsPage';
import ListingPage from './pages/ListingPage';
import NotFoundPage from './pages/NotFoundPage';
import NotificationsPage from './pages/NotificationsPage';
import PremiumPage from './pages/PremiumPage';
import ProfilePage from './pages/ProfilePage';
import SavedSearchesPage from './pages/SavedSearchesPage';
import SearchPage from './pages/SearchPage';
import SoonPage from './pages/SoonPage';
import TestCardPage from './pages/TestCardPage';
import { AuthProvider } from './providers/AuthProvider';
import { I18nProvider } from './providers/I18nProvider';
import { ToastProvider } from './providers/ToastProvider';

const router = createBrowserRouter(
  [
    {
      element: <Layout />,
      children: [
        { path: '/', element: <HomePage /> },
        { path: '/search', element: <SearchPage /> },
        { path: '/listing/:id', element: <ListingPage /> },
        // Гостиницы (FRONTEND-045): отдельный раздел, с квартирами не смешивается
        { path: HOTELS_PATH, element: <HotelsPage /> },
        { path: `${HOTELS_PATH}/:id`, element: <HotelPage /> },
        { path: MY_HOTELS_PATH, element: <MyHotelsPage /> },
        // key: «Разместить» и «Изменить» — разные формы, состояние не переносится
        { path: NEW_HOTEL_PATH, element: <HotelFormPage key="new" /> },
        { path: `${MY_HOTELS_PATH}/:id/edit`, element: <HotelFormPage key="edit" /> },
        { path: '/help', element: <HelpPage /> },
        { path: '/legal/:doc', element: <LegalPage /> },
        // Посуточная аренда — та же лента в режиме «Посуточно»
        { path: '/daily', element: <Navigate to={DAILY_SEARCH_PATH} replace /> },
        // Разделы главного меню без своей страницы — заглушка «Скоро» (FRONTEND-029, 031, 033)
        { path: '/smart', element: <SoonPage feature="smart" /> },
        { path: '/my-listings', element: <SoonPage feature="owner" /> },
        { path: '/invite', element: <SoonPage feature="invite" /> },
        { path: '/favorites', element: <FavoritesPage /> },
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
