import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiPost } from '../api/client';
import type { MyListing, MyListings } from '../api/types';
import FormStepper from '../components/FormStepper';
import ListingFormAbout from '../components/ListingFormAbout';
import ListingFormContact from '../components/ListingFormContact';
import ListingFormFlat from '../components/ListingFormFlat';
import ListingFormPlace from '../components/ListingFormPlace';
import ListingPhotos from '../components/ListingPhotos';
import OpenInTelegram from '../components/OpenInTelegram';
import { useApi } from '../hooks/useApi';
import { useCity } from '../hooks/useCity';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBack } from '../hooks/useTelegramBackButton';
import {
  DEFAULT_LISTINGS_LIMIT,
  LISTING_FORM_STEPS,
  MY_LISTINGS_PATH,
  emptyListingDraft,
  listingErrorText,
  listingStepProblems,
  toListingInput,
  type ListingDraft,
} from '../lib/ownerListings';
import { cityCodes } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

const BUTTON_CLASS =
  'inline-flex min-h-12 items-center justify-center gap-2 rounded-[var(--radius-md)] px-5 py-3 text-sm font-semibold transition-colors active:scale-[.98] disabled:opacity-60';
const PRIMARY_CLASS = `${BUTTON_CLASS} flex-1 bg-[var(--primary)] text-white shadow-[var(--shadow-sm)] hover:bg-[var(--primary-hover)]`;
const SECONDARY_CLASS = `${BUTTON_CLASS} border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--surface-hover)]`;
const CONTACT_STEP = LISTING_FORM_STEPS.indexOf('contact');
const PHOTOS_STEP = LISTING_FORM_STEPS.indexOf('photos');

/**
 * Размещение квартиры по шагам: где → квартира и цена → описание и удобства → контакт → фото.
 * На шаге «Контакт» объявление создаётся и сразу попадает в поиск; фото добавляются к нему.
 * Правки готового объявления API не принимает, поэтому с шага фото назад не возвращаемся.
 */
export default function ListingFormPage() {
  const navigate = useNavigate();
  const { t } = useI18n();
  const ft = t.listing_form;
  const hf = t.hotel_form;
  const showToast = useToast();
  const { user, loading: authLoading } = useAuth();
  const { city } = useCity();
  // Лимит объявлений — для текста ошибки 409
  const mine = useApi<MyListings>(user ? '/api/my/listings' : null);
  const [draft, setDraft] = useState<ListingDraft>(() => {
    const [only, ...others] = cityCodes(city);
    return emptyListingDraft(others.length === 0 ? (only ?? '') : '');
  });
  const [listing, setListing] = useState<MyListing | null>(null);
  const [step, setStep] = useState(0);
  const [problems, setProblems] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const stepKey = LISTING_FORM_STEPS[step] ?? 'place';
  useDocumentTitle(`${ft.title} — bina.ai`);

  const goBack = () => {
    setProblems([]);
    if (step > 0 && !listing) setStep(step - 1);
    else navigate(MY_LISTINGS_PATH);
  };
  // «Назад» Telegram листает шаги, с первого и с фото — уводит к списку
  useTelegramBack(goBack);

  const change = (patch: Partial<ListingDraft>) => {
    setProblems([]);
    setDraft((current) => ({ ...current, ...patch }));
  };

  const publish = async () => {
    setBusy(true);
    try {
      setListing(await apiPost<MyListing>('/api/my/listings', toListingInput(draft)));
      haptic('success');
      showToast(ft.published, 'success');
      setStep(PHOTOS_STEP);
      window.scrollTo({ top: 0 });
    } catch (error) {
      haptic('error');
      setProblems([listingErrorText(error, ft, mine.data?.limit ?? DEFAULT_LISTINGS_LIMIT)]);
    } finally {
      setBusy(false);
    }
  };

  const next = () => {
    if (busy) return;
    const found = listingStepProblems(stepKey, draft, ft, Boolean(user?.username));
    if (found.length > 0) {
      haptic('error');
      setProblems(found);
      return;
    }
    haptic('light');
    setProblems([]);
    if (step === PHOTOS_STEP) navigate(MY_LISTINGS_PATH);
    else if (step === CONTACT_STEP) void publish();
    else {
      setStep(step + 1);
      window.scrollTo({ top: 0 });
    }
  };

  if (!user && !authLoading) {
    return (
      <section className="listing-form mx-auto w-full max-w-md py-6">
        <OpenInTelegram />
      </section>
    );
  }

  let nextLabel = hf.next;
  if (step === CONTACT_STEP) nextLabel = hf.publish;
  if (step === PHOTOS_STEP) nextLabel = hf.done;

  return (
    <section
      className="listing-form mx-auto flex w-full max-w-xl flex-col gap-6"
      aria-labelledby="listing-form-title"
    >
      <h1 id="listing-form-title" className="pt-2 text-2xl font-bold tracking-tight sm:text-3xl">
        {ft.title}
      </h1>
      <FormStepper current={step + 1} total={LISTING_FORM_STEPS.length} title={ft.steps[stepKey]} />

      <form
        className="listing-form__step flex flex-col gap-5 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)]"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          next();
        }}
      >
        {stepKey === 'place' && <ListingFormPlace draft={draft} onChange={change} />}
        {stepKey === 'flat' && <ListingFormFlat draft={draft} onChange={change} />}
        {stepKey === 'about' && <ListingFormAbout draft={draft} onChange={change} />}
        {stepKey === 'contact' && <ListingFormContact draft={draft} onChange={change} />}
        {stepKey === 'photos' && listing && (
          <ListingPhotos listing={listing} onChange={setListing} />
        )}

        {problems.length > 0 && (
          <ul
            className="listing-form__problems m-0 flex list-none flex-col gap-1 rounded-[var(--radius-md)] border border-[var(--danger-border)] bg-[var(--danger-bg)] px-4 py-3 text-sm font-medium text-[var(--danger-text)]"
            role="alert"
          >
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        )}

        <footer className="listing-form__actions flex gap-3">
          {!listing && (
            <button type="button" className={SECONDARY_CLASS} disabled={busy} onClick={goBack}>
              {step === 0 ? t.common.cancel : hf.back}
            </button>
          )}
          <button type="submit" className={PRIMARY_CLASS} disabled={busy} aria-busy={busy}>
            {busy && <span className="spinner" aria-hidden="true" />}
            {nextLabel}
          </button>
        </footer>
      </form>
    </section>
  );
}
