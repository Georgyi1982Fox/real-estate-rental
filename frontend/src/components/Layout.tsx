import { Outlet, ScrollRestoration, useMatch } from 'react-router-dom';
import { useReferralApply } from '../hooks/useReferral';
import { useAuth } from '../providers/AuthProvider';
import BottomNav from './BottomNav';
import type { NavMode } from './BottomNav';
import Header from './Header';
import Footer from './Footer';
import PremiumLimitModal from './PremiumLimitModal';
import ReferralBanner from './ReferralBanner';

export default function Layout() {
  const { isInTelegram } = useAuth();
  // Запуск по ссылке друга: код уходит на бэкенд один раз
  useReferralApply();
  // На странице объявления панели нет: в Telegram там внизу нативная кнопка «Написать»
  const onListing = useMatch('/listing/:id') !== null;
  const nav: NavMode = onListing ? 'none' : isInTelegram ? 'always' : 'mobile';

  return (
    <>
      <Header nav={nav} />
      <main
        id="main-content"
        className="app-main mx-auto w-full max-w-screen-xl px-4 pb-24 pt-4 sm:px-6 lg:px-8"
      >
        <ReferralBanner />
        <Outlet />
      </main>
      <Footer nav={nav} />
      {nav !== 'none' && <BottomNav mode={nav} />}
      <PremiumLimitModal />
      <ScrollRestoration />
    </>
  );
}
