import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { AgencyCabinet } from '../api/types';
import AgencyHeader from '../components/AgencyHeader';
import AgencyListingCard from '../components/AgencyListingCard';
import AgencyPackages from '../components/AgencyPackages';
import AgencyPlanCard from '../components/AgencyPlanCard';
import AgencyRegisterForm from '../components/AgencyRegisterForm';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Icon from '../components/Icon';
import OpenInTelegram from '../components/OpenInTelegram';
import SavedSearchSkeleton from '../components/SavedSearchSkeleton';
import StatTile from '../components/StatTile';
import { useApi } from '../hooks/useApi';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { AGENCY_API, agencyTotals } from '../lib/agency';
import { NEW_LISTING_PATH } from '../lib/ownerListings';
import { MORE_PATH } from '../lib/paths';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';

const SKELETON_COUNT = 3;
const ADD_CLASS =
  'inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-4 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]';

/** «💼 Кабинет агентства»: регистрация, пакет, статистика за 30 дней, Premium и пакеты в боте */
export default function AgencyCabinetPage() {
  const { t } = useI18n();
  const at = t.agency;
  const { user, loading: authLoading } = useAuth();
  const { data, error, loading, reload } = useApi<AgencyCabinet>(user ? AGENCY_API : null);
  // Регистрация и правки: сервер каждый раз отдаёт кабинет целиком
  const [saved, setSaved] = useState<AgencyCabinet | null>(null);
  const agency = saved ?? data;

  useDocumentTitle(`${at.page_title} — bina.ai`);
  useTelegramBackButton(MORE_PATH);

  if ((!user && !authLoading) || error?.isUnauthorized) {
    return (
      <section className="agency mx-auto w-full max-w-md py-6">
        <OpenInTelegram />
      </section>
    );
  }

  if (!agency && error?.isNotFound) {
    return (
      <section className="agency mx-auto w-full max-w-2xl py-2 sm:py-4">
        <AgencyRegisterForm onRegistered={setSaved} onExists={reload} />
      </section>
    );
  }

  if (!agency) {
    return (
      <section className="agency mx-auto flex w-full max-w-2xl flex-col gap-4 py-2 sm:py-4">
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{at.page_title}</h1>
        {error ? (
          <ErrorState onRetry={reload} />
        ) : (
          (loading || authLoading) && (
            <ul className="m-0 flex list-none flex-col gap-4 p-0" aria-hidden="true">
              {Array.from({ length: SKELETON_COUNT }, (_, index) => (
                <li key={index}>
                  <SavedSearchSkeleton />
                </li>
              ))}
            </ul>
          )
        )}
      </section>
    );
  }

  const totals = agencyTotals(agency.listings);
  const canAdd = !agency.blocked && agency.active < agency.limit;
  const addLink = (
    <Link to={NEW_LISTING_PATH} className={ADD_CLASS} onClick={() => haptic('light')}>
      <Icon name="plus" className="size-4" />
      {t.my_listings.add}
    </Link>
  );

  return (
    <section
      className="agency mx-auto flex w-full max-w-2xl flex-col gap-6 py-2 sm:py-4"
      aria-labelledby="agency-title"
    >
      <AgencyHeader agency={agency} onChange={setSaved} />

      {agency.blocked ? (
        <p className="m-0 rounded-[var(--radius-md)] bg-[var(--danger-bg)] px-3 py-2 text-sm font-medium text-[var(--danger-text)]">
          {at.blocked}
        </p>
      ) : (
        <AgencyPlanCard agency={agency} />
      )}

      <section className="agency-stats flex flex-col gap-3" aria-labelledby="agency-stats-title">
        <h2 id="agency-stats-title" className="text-lg font-semibold">
          {at.stats_title}
        </h2>
        <ul className="m-0 grid list-none grid-cols-2 gap-3 p-0 sm:grid-cols-4">
          <li>
            <StatTile icon="eye" label={at.stats.views} value={totals.views} />
          </li>
          <li>
            <StatTile icon="phone" label={at.stats.contacts} value={totals.contacts} />
          </li>
          <li>
            <StatTile icon="message" label={at.stats.chats} value={totals.chats} />
          </li>
          <li>
            <StatTile icon="calendar_check" label={at.stats.viewings} value={totals.viewings} />
          </li>
        </ul>
      </section>

      <section
        className="agency-listings flex flex-col gap-3"
        aria-labelledby="agency-listings-title"
      >
        <header className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="agency-listings-title" className="text-lg font-semibold">
            {at.listings_title}
          </h2>
          {canAdd && agency.listings.length > 0 && addLink}
        </header>
        {agency.listings.length === 0 ? (
          <EmptyState title={t.my_listings.empty_title} text={at.empty_text}>
            {canAdd && addLink}
          </EmptyState>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-4 p-0">
            {agency.listings.map((item) => (
              <li key={item.listing.id}>
                <AgencyListingCard item={item} blocked={agency.blocked} />
              </li>
            ))}
          </ul>
        )}
      </section>

      {!agency.blocked && <AgencyPackages agency={agency} />}
    </section>
  );
}
