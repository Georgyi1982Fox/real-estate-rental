import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiDelete, apiPost, apiPut } from '../api/client';
import type { HotelRoomInput, MyHotel, MyHotels } from '../api/types';
import ErrorState from '../components/ErrorState';
import FormStepper from '../components/FormStepper';
import HotelFormContacts from '../components/HotelFormContacts';
import HotelFormDescription from '../components/HotelFormDescription';
import HotelFormDetails from '../components/HotelFormDetails';
import HotelFormMain from '../components/HotelFormMain';
import HotelFormPlace from '../components/HotelFormPlace';
import HotelPhotos from '../components/HotelPhotos';
import HotelRoomsEditor from '../components/HotelRoomsEditor';
import ListingSkeleton from '../components/ListingSkeleton';
import OpenInTelegram from '../components/OpenInTelegram';
import { useApi } from '../hooks/useApi';
import { useCity } from '../hooks/useCity';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBack } from '../hooks/useTelegramBackButton';
import {
  HOTEL_FORM_STEPS,
  draftFromHotel,
  emptyDraft,
  hotelErrorTexts,
  stepProblems,
  toHotelInput,
  type HotelDraft,
} from '../lib/hotelForm';
import { MY_HOTELS_PATH } from '../lib/hotels';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import NotFoundPage from './NotFoundPage';

const BUTTON_CLASS =
  'inline-flex min-h-12 items-center justify-center gap-2 rounded-[var(--radius-md)] px-5 py-3 text-sm font-semibold transition-colors active:scale-[.98] disabled:opacity-60';
const PRIMARY_CLASS = `${BUTTON_CLASS} flex-1 bg-[var(--primary)] text-white shadow-[var(--shadow-sm)] hover:bg-[var(--primary-hover)]`;
const SECONDARY_CLASS = `${BUTTON_CLASS} border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--surface-hover)]`;
/** Сколько объектов можно держать включёнными, пока сервер не сказал точнее */
const DEFAULT_LIMIT = 5;
const CONTACTS_STEP = HOTEL_FORM_STEPS.indexOf('contacts');
const PHOTOS_STEP = HOTEL_FORM_STEPS.indexOf('photos');

/**
 * Форма размещения и изменения гостиницы по шагам: тип и название → город, адрес, точка →
 * звёзды, удобства, заезд/выезд → описание → номера → контакты → фото.
 *
 * Объект создаётся на шаге «Контакты» (POST со всеми номерами); фото добавляются уже к
 * созданному. У готового объекта номера и фото меняются сразу, своими запросами.
 */
export default function HotelFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { lang, t } = useI18n();
  const ft = t.hotel_form;
  const showToast = useToast();
  const { user, loading: authLoading } = useAuth();
  const { city } = useCity();
  const existing = useApi<MyHotel>(id && user ? `/api/my/hotels/${encodeURIComponent(id)}` : null);
  // Лимит объектов — для текста ошибки 409
  const mine = useApi<MyHotels>(user ? '/api/my/hotels' : null);
  // Сохранённый объект: загруженный («Изменить») или только что размещённый
  const [hotel, setHotel] = useState<MyHotel | null>(null);
  const [draft, setDraft] = useState<HotelDraft>(() => emptyDraft(city ?? ''));
  const [step, setStep] = useState(0);
  const [problems, setProblems] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  // «Изменить»: форма начинается с данных объекта
  if (existing.data && hotel === null) {
    setHotel(existing.data);
    setDraft(draftFromHotel(existing.data, lang));
  }

  const stepKey = HOTEL_FORM_STEPS[step] ?? 'main';
  const title = id ? ft.title_edit : ft.title_new;
  useDocumentTitle(`${title} — bina.ai`);

  const goBack = () => {
    setProblems([]);
    if (step > 0) setStep(step - 1);
    else navigate(MY_HOTELS_PATH);
  };
  // «Назад» Telegram листает шаги, с первого — уводит к списку
  useTelegramBack(goBack);

  const change = (patch: Partial<HotelDraft>) => {
    setProblems([]);
    setDraft((current) => ({ ...current, ...patch }));
  };

  /** Сервер отдал объект целиком: номера и фото в форме — как на сервере */
  const accept = (saved: MyHotel) => {
    setHotel(saved);
    setDraft((current) => ({ ...current, rooms: draftFromHotel(saved, lang).rooms }));
  };

  const fail = (error: unknown) => {
    haptic('error');
    setProblems(hotelErrorTexts(error, ft, mine.data?.limit ?? DEFAULT_LIMIT));
  };

  const saveRoom = async (room: HotelRoomInput, index: number | null): Promise<boolean> => {
    setProblems([]);
    // До размещения номера живут в черновике и уйдут на сервер вместе с объектом
    if (!hotel) {
      setDraft((current) => ({
        ...current,
        rooms:
          index === null
            ? [...current.rooms, room]
            : current.rooms.map((item, position) => (position === index ? room : item)),
      }));
      return true;
    }
    const base = `/api/my/hotels/${hotel.id}/rooms`;
    const roomId = index === null ? undefined : hotel.rooms[index]?.id;
    try {
      accept(
        roomId === undefined
          ? await apiPost<MyHotel>(base, room)
          : await apiPut<MyHotel>(`${base}/${roomId}`, room),
      );
      return true;
    } catch (error) {
      fail(error);
      return false;
    }
  };

  const removeRoom = async (index: number): Promise<boolean> => {
    setProblems([]);
    if (!hotel) {
      setDraft((current) => ({
        ...current,
        rooms: current.rooms.filter((_, position) => position !== index),
      }));
      return true;
    }
    const roomId = hotel.rooms[index]?.id;
    if (roomId === undefined) return false;
    try {
      accept(await apiDelete<MyHotel>(`/api/my/hotels/${hotel.id}/rooms/${roomId}`));
      return true;
    } catch (error) {
      fail(error);
      return false;
    }
  };

  /** Разместить новый объект или сохранить изменения — и перейти к фото */
  const save = async () => {
    setBusy(true);
    try {
      const body = toHotelInput(draft);
      const saved = hotel
        ? await apiPut<MyHotel>(`/api/my/hotels/${hotel.id}`, body)
        : await apiPost<MyHotel>('/api/my/hotels', body);
      accept(saved);
      haptic('success');
      showToast(hotel ? ft.saved : ft.published, 'success');
      setStep(PHOTOS_STEP);
      window.scrollTo({ top: 0 });
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  };

  const next = () => {
    const found = stepProblems(stepKey, draft, ft, Boolean(user?.username));
    if (found.length > 0) {
      haptic('error');
      setProblems(found);
      return;
    }
    haptic('light');
    setProblems([]);
    if (step === PHOTOS_STEP) navigate(MY_HOTELS_PATH);
    else if (step === CONTACTS_STEP) void save();
    else {
      setStep(step + 1);
      window.scrollTo({ top: 0 });
    }
  };

  if (!user && !authLoading) {
    return (
      <section className="hotel-form mx-auto w-full max-w-md py-6">
        <OpenInTelegram />
      </section>
    );
  }
  if (id && existing.error?.isNotFound) return <NotFoundPage />;
  if (id && existing.error) return <ErrorState onRetry={existing.reload} />;
  if (id && !hotel) return <ListingSkeleton />;

  let nextLabel = ft.next;
  if (step === CONTACTS_STEP) nextLabel = hotel ? ft.save : ft.publish;
  if (step === PHOTOS_STEP) nextLabel = ft.done;

  return (
    <section className="hotel-form mx-auto flex w-full max-w-xl flex-col gap-6" aria-labelledby="hotel-form-title">
      <h1 id="hotel-form-title" className="pt-2 text-2xl font-bold tracking-tight sm:text-3xl">
        {title}
      </h1>
      <FormStepper current={step + 1} total={HOTEL_FORM_STEPS.length} title={ft.steps[stepKey]} />

      <form
        className="hotel-form__step flex flex-col gap-5 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)]"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          next();
        }}
      >
        {stepKey === 'main' && <HotelFormMain draft={draft} onChange={change} />}
        {stepKey === 'place' && <HotelFormPlace draft={draft} onChange={change} />}
        {stepKey === 'details' && <HotelFormDetails draft={draft} onChange={change} />}
        {stepKey === 'description' && <HotelFormDescription draft={draft} onChange={change} />}
        {stepKey === 'rooms' && (
          <HotelRoomsEditor rooms={draft.rooms} onSave={saveRoom} onRemove={removeRoom} />
        )}
        {stepKey === 'contacts' && <HotelFormContacts draft={draft} onChange={change} />}
        {stepKey === 'photos' && hotel && <HotelPhotos hotel={hotel} onChange={setHotel} />}

        {problems.length > 0 && (
          <ul
            className="hotel-form__problems m-0 flex list-none flex-col gap-1 rounded-[var(--radius-md)] border border-[var(--danger-border)] bg-[var(--danger-bg)] px-4 py-3 text-sm font-medium text-[var(--danger-text)]"
            role="alert"
          >
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        )}

        <footer className="hotel-form__actions flex gap-3">
          {/* С шага фото назад не ходим только по кнопке «Готово»: объект уже сохранён */}
          <button type="button" className={SECONDARY_CLASS} disabled={busy} onClick={goBack}>
            {step === 0 ? t.common.cancel : ft.back}
          </button>
          <button type="submit" className={PRIMARY_CLASS} disabled={busy} aria-busy={busy}>
            {busy && <span className="spinner" aria-hidden="true" />}
            {nextLabel}
          </button>
        </footer>
      </form>
    </section>
  );
}
