import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiPatch } from '../api/client';
import type { ListingId, MyListing, MyListings } from '../api/types';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Icon from '../components/Icon';
import ListingPhotos from '../components/ListingPhotos';
import ListingPriceModal from '../components/ListingPriceModal';
import Modal from '../components/Modal';
import MyListingCard from '../components/MyListingCard';
import OpenInTelegram from '../components/OpenInTelegram';
import SavedSearchSkeleton from '../components/SavedSearchSkeleton';
import { useApi } from '../hooks/useApi';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { fill, fillVars } from '../lib/format';
import { DEFAULT_LISTINGS_LIMIT, NEW_LISTING_PATH, listingErrorText } from '../lib/ownerListings';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

const SKELETON_COUNT = 2;
const ADD_CLASS =
  'inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-4 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98] disabled:opacity-60';

/** «Мои объявления» (вкладка «Сдать»): статус, снять / вернуть, цена, фото, размещение */
export default function MyListingsPage() {
  const { t } = useI18n();
  const mt = t.my_listings;
  const showToast = useToast();
  const { user, loading: authLoading } = useAuth();
  const { data, error, loading, reload } = useApi<MyListings>(user ? '/api/my/listings' : null);
  // Правки поверх ответа сервера
  const [changed, setChanged] = useState<Record<string, MyListing>>({});
  const [busyId, setBusyId] = useState<ListingId | null>(null);
  const [pricing, setPricing] = useState<MyListing | null>(null);
  const [photosId, setPhotosId] = useState<ListingId | null>(null);
  // Стабильные ссылки: Modal перезапускает эффект (фокус) при смене onClose
  const closePrice = useCallback(() => setPricing(null), []);
  const closePhotos = useCallback(() => setPhotosId(null), []);

  useDocumentTitle(`${mt.page_title} — bina.ai`);
  useTelegramBackButton('/');

  const listings = (data?.items ?? []).map((item) => changed[String(item.id)] ?? item);
  const limit = data?.limit ?? DEFAULT_LISTINGS_LIMIT;
  const active = listings.filter((listing) => listing.status === 'active').length;
  const full = active >= limit;
  const photosOf = listings.find((listing) => listing.id === photosId) ?? null;

  const accept = useCallback(
    (saved: MyListing) => setChanged((current) => ({ ...current, [String(saved.id)]: saved })),
    [],
  );

  /** PATCH с индикатором на карточке; true — сохранено */
  const patch = async (listing: MyListing, body: object, done: string): Promise<boolean> => {
    setBusyId(listing.id);
    try {
      accept(await apiPatch<MyListing>(`/api/my/listings/${listing.id}`, body));
      haptic('success');
      showToast(done, 'success');
      return true;
    } catch (failure) {
      haptic('error');
      showToast(listingErrorText(failure, t.listing_form, limit), 'error');
      return false;
    } finally {
      setBusyId(null);
    }
  };

  const savePrice = async (price: number, currency: string) => {
    if (pricing && (await patch(pricing, { price, currency }, mt.price_saved))) setPricing(null);
  };

  if (!user && !authLoading) {
    return (
      <section className="my-listings mx-auto w-full max-w-md py-6">
        <OpenInTelegram />
      </section>
    );
  }

  const addLink = (
    <Link to={NEW_LISTING_PATH} className={ADD_CLASS} onClick={() => haptic('light')}>
      <Icon name="plus" className="size-4" />
      {mt.add}
    </Link>
  );

  return (
    <section
      className="my-listings mx-auto flex w-full max-w-2xl flex-col gap-6"
      aria-labelledby="my-listings-title"
    >
      <header className="flex flex-wrap items-center justify-between gap-3 py-2 sm:py-4">
        <div className="min-w-0 space-y-1">
          <h1 id="my-listings-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
            {mt.page_title}
          </h1>
          {data && listings.length > 0 && (
            <p className="m-0 text-sm text-[var(--text-secondary)]">
              {fillVars(mt.active_count, { n: active, limit })}
            </p>
          )}
        </div>
        {listings.length > 0 &&
          (full ? (
            <button type="button" className={ADD_CLASS} disabled>
              <Icon name="plus" className="size-4" />
              {mt.add}
            </button>
          ) : (
            addLink
          ))}
      </header>

      {listings.length > 0 && full && (
        <p className="m-0 rounded-[var(--radius-md)] bg-[var(--warning-bg)] px-3 py-2 text-sm font-medium text-[var(--warning-text)]">
          {fill(t.listing_form.errors.limit, limit)}
        </p>
      )}

      {(loading || authLoading) && (
        <ul className="m-0 flex list-none flex-col gap-4 p-0" aria-hidden="true">
          {Array.from({ length: SKELETON_COUNT }, (_, index) => (
            <li key={index}>
              <SavedSearchSkeleton />
            </li>
          ))}
        </ul>
      )}

      {error && !error.isUnauthorized && <ErrorState onRetry={reload} />}
      {error?.isUnauthorized && <OpenInTelegram />}

      {data && listings.length === 0 && (
        <EmptyState title={mt.empty_title} text={mt.empty_text}>
          {addLink}
        </EmptyState>
      )}

      {listings.length > 0 && (
        <ul className="m-0 flex list-none flex-col gap-4 p-0">
          {listings.map((listing) => (
            <li key={listing.id}>
              <MyListingCard
                listing={listing}
                busy={busyId === listing.id}
                onToggle={(next) =>
                  void patch(listing, { active: next }, next ? mt.put_back_done : mt.taken_down)
                }
                onPrice={() => setPricing(listing)}
                onPhotos={() => setPhotosId(listing.id)}
              />
            </li>
          ))}
        </ul>
      )}

      <ListingPriceModal
        listing={pricing}
        busy={busyId !== null}
        onSubmit={(price, currency) => void savePrice(price, currency)}
        onClose={closePrice}
      />
      <Modal open={photosOf !== null} title={mt.photos} onClose={closePhotos}>
        {photosOf && <ListingPhotos listing={photosOf} onChange={accept} />}
      </Modal>
    </section>
  );
}
