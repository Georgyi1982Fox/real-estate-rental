import { Outlet, ScrollRestoration } from 'react-router-dom';
import Header from './Header';
import Footer from './Footer';

export default function Layout() {
  return (
    <>
      <Header />
      <main
        id="main-content"
        className="app-main mx-auto w-full max-w-screen-xl px-4 pb-24 pt-4 sm:px-6 lg:px-8"
      >
        <Outlet />
      </main>
      <Footer />
      <ScrollRestoration />
    </>
  );
}
