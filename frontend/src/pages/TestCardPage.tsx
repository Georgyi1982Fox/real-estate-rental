import type { Listing } from '../api/types';
import ListingCard from '../components/ListingCard';
import { useDocumentTitle } from '../hooks/useDocumentTitle';

// Dev-страница FRONTEND-002: два состояния карточки (с фото / без фото)
const TEST_LISTINGS: Listing[] = [
  {
    id: 1,
    title: { ka: 'ბინა საბურთალოზე', ru: 'Квартира в Сабуртало', en: 'Apartment in Saburtalo' },
    price: 1200,
    currency: 'GEL',
    rooms: 2,
    area: 65,
    district: 'Сабуртало',
    images: ['https://static.ss.ge/20260921/19_97b5d109-2456-48e9-9669-88613204ad8c_Thumb.jpg'],
  },
  {
    id: 2,
    title: { ka: 'ბინა ვაკეში', ru: 'Квартира в Ваке', en: 'Apartment in Vake' },
    price: 1800,
    currency: 'GEL',
    rooms: 3,
    area: 82,
    district: 'Ваке',
    images: [],
  },
];

export default function TestCardPage() {
  useDocumentTitle('Тест карточки — Bina.ai');

  return (
    <section aria-labelledby="test-card-title" className="mx-auto w-full max-w-6xl">
      <header className="mb-6">
        <p className="text-sm font-medium text-[var(--primary)]">FRONTEND-002</p>
        <h1 id="test-card-title" className="mt-1 text-2xl font-bold text-[var(--text-primary)]">
          Тест карточки квартиры
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-secondary)]">
          Mock-страница для проверки адаптивности, hover-эффекта и favorite toggle.
        </p>
      </header>

      <section aria-label="Тестовые объявления" className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {TEST_LISTINGS.map((listing) => (
          <ListingCard key={listing.id} listing={listing} />
        ))}
      </section>
    </section>
  );
}
