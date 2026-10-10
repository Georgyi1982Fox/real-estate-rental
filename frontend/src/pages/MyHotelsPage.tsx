import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiDelete, apiPatch } from '../api/client';
import type { HotelId, MyHotel, MyHotels } from '../api/types';
import ConfirmDialog from '../components/ConfirmDialog';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Icon from '../components/Icon';
import MyHotelCard from '../components/MyHotelCard';
import OpenInTelegram from '../components/OpenInTelegram';
import SavedSearchSkeleton from '../components/SavedSearchSkeleton';
import { useApi } from '../hooks/useApi';
import { useCity } from '../hooks/useCity';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { fill, fillVars, tr } from '../lib/format';
import { hotelErrorTexts } from '../lib/hotelForm';
import { NEW_HOTEL_PATH } from '../lib/hotels';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

const SKELETON_COUNT = 2;
const ADD_CLASS =
  'inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-4 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]';

/** «Мои гостиницы»: свои объекты со статусом, размещение, изменение, снять / вернуть, удаление */
export default function MyHotelsPage() {
  const { lang, t } = useI18n();
  const mt = t.my_hotels;
  const showToast = useToast();
  const { user, loading: authLoading } = useAuth();
  const { names: cityNames } = useCity();
  const { data, error, loading, reload } = useApi<MyHotels>(user ? '/api/my/hotels' : null);
  // Правки поверх ответа сервера: изменённые объекты и удалённые ID
  const [changed, setChanged] = useState<Record<string, MyHotel>>({});
  const [removed, setRemoved] = useState<string[]>([]);
  const [busyId, setBusyId] = useState<HotelId | null>(null);
  const [deleting, setDeleting] = useState<MyHotel | null>(null);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeDelete = useCallback(() => setDeleting(null), []);

  useDocumentTitle(`${mt.page_title} — bina.ai`);
  useTelegramBackButton('/');

  const hotels = (data?.items ?? [])
    .filter((hotel) => !removed.includes(String(hotel.id)))
    .map((hotel) => changed[String(hotel.id)] ?? hotel);
  const limit = data?.limit ?? 0;
  const active = hotels.filter((hotel) => hotel.status === 'active').length;

  const fail = (failure: unknown) => {
    haptic('error');
    showToast(hotelErrorTexts(failure, t.hotel_form, limit)[0] ?? '', 'error');
  };

  const toggle = async (hotel: MyHotel, next: boolean) => {
    setBusyId(hotel.id);
    try {
      const saved = await apiPatch<MyHotel>(`/api/my/hotels/${hotel.id}`, { active: next });
      setChanged((current) => ({ ...current, [String(saved.id)]: saved }));
      haptic('success');
      showToast(next ? mt.put_back_done : mt.taken_down, 'success');
    } catch (failure) {
      fail(failure);
    } finally {
      setBusyId(null);
    }
  };

  const remove = async () => {
    if (!deleting) return;
    setBusyId(deleting.id);
    try {
      await apiDelete(`/api/my/hotels/${deleting.id}`);
      setRemoved((current) => [...current, String(deleting.id)]);
      setDeleting(null);
      haptic('success');
      showToast(mt.deleted, 'success');
    } catch (failure) {
      fail(failure);
    } finally {
      setBusyId(null);
    }
  };

  if (!user && !authLoading) {
    return (
      <section className="my-hotels mx-auto w-full max-w-md py-6">
        <OpenInTelegram />
      </section>
    );
  }

  const addLink = (
    <Link to={NEW_HOTEL_PATH} className={ADD_CLASS} onClick={() => haptic('light')}>
      <Icon name="plus" className="size-4" />
      {mt.add}
    </Link>
  );

  return (
    <section className="my-hotels mx-auto flex w-full max-w-2xl flex-col gap-6" aria-labelledby="my-hotels-title">
      <header className="flex flex-wrap items-center justify-between gap-3 py-2 sm:py-4">
        <div className="min-w-0 space-y-1">
          <h1 id="my-hotels-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
            {mt.page_title}
          </h1>
          {data && hotels.length > 0 && (
            <p className="m-0 text-sm text-[var(--text-secondary)]">
              {fillVars(mt.active_count, { n: active, limit })}
            </p>
          )}
        </div>
        {hotels.length > 0 && addLink}
      </header>

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

      {data && hotels.length === 0 && (
        <EmptyState icon="🏨" title={mt.empty_title} text={mt.empty_text}>
          {addLink}
        </EmptyState>
      )}

      {hotels.length > 0 && (
        <ul className="m-0 flex list-none flex-col gap-4 p-0">
          {hotels.map((hotel) => (
            <li key={hotel.id}>
              <MyHotelCard
                hotel={hotel}
                cityNames={cityNames}
                busy={busyId === hotel.id}
                onToggle={(next) => void toggle(hotel, next)}
                onDelete={() => setDeleting(hotel)}
              />
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={deleting !== null}
        title={mt.delete_title}
        text={fill(mt.delete_text, deleting ? tr(deleting.name, lang) : '')}
        confirmLabel={mt.delete}
        danger
        busy={busyId !== null}
        onConfirm={() => void remove()}
        onClose={closeDelete}
      />
    </section>
  );
}
