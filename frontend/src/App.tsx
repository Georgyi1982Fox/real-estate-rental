import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import ListingPage from './pages/ListingPage';
import NotFoundPage from './pages/NotFoundPage';
import TestCardPage from './pages/TestCardPage';
import { I18nProvider } from './providers/I18nProvider';
import { ToastProvider } from './providers/ToastProvider';

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <HomePage /> },
      { path: '/listing/:id', element: <ListingPage /> },
      { path: '/test_card', element: <TestCardPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

export default function App() {
  return (
    <I18nProvider>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </I18nProvider>
  );
}
