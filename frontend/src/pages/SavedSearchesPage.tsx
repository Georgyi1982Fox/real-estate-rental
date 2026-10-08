import { useCallback, useState } from 'react';
import type { SavedSearch } from '../api/types';
import { Link } from 'react-router-dom';
import ConfirmDialog from '../components/ConfirmDialog';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import OpenInTelegram from '../components/OpenInTelegram';
import RenameSearchModal from '../components/RenameSearchModal';
import SavedSearchCard from '../components/SavedSearchCard';
import SavedSearchSkeleton from '../components/SavedSearchSkeleton';
import { useCity } from '../hooks/useCity';
import { useDistricts } from '../hooks/useDistricts';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useSavedSearches } from '../hooks/useSavedSearches';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { fill } from '../lib/format';
import { describeFilters, districtsLabel, filterDistricts } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

const SKELETON_COUNT = 3;

/** Открытая модалка: переименование или удаление конкретного поиска */
type Dialog = { kind: 'rename' | 'delete'; id: string } | null;

export default function SavedSearchesPage() {
  const { t, lang } = useI18n();
  const st = t.searches;
  const showToast = useToast();
  const { names } = useDistricts();
  const { names: cityNames } = useCity();
  const { searches, loading, error, unauthorized, reload, rename, toggleNotify, remove, markSeen } =
    useSavedSearches();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [busy, setBusy] = useState(false);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeDialog = useCallback(() => setDialog(null), []);

  useDocumentTitle(`${st.page_title} — bina.ai`);
  useTelegramBackButton('/');

  const districtName = (search: SavedSearch) =>
    districtsLabel(filterDistricts(search.filters), names, lang);
  const titleOf = (id: string) => {
    const search = searches.find((item) => item.id === id);
    if (!search) return '';
    return search.name.trim() || describeFilters(search.filters, districtName(search), st);
  };
  const dialogTitle = dialog ? titleOf(dialog.id) : '';

  const submitRename = async (name: string) => {
    if (!dialog) return;
    setBusy(true);
    const ok = await rename(dialog.id, name);
    setBusy(false);
    if (!ok) return;
    setDialog(null);
    showToast(st.renamed_toast, 'success');
    haptic('success');
  };

  const confirmDelete = async () => {
    if (!dialog) return;
    setBusy(true);
    const ok = await remove(dialog.id);
    setBusy(false);
    if (!ok) return;
    setDialog(null);
    showToast(st.deleted_toast, 'success');
    haptic('success');
  };

  let content;
  if (unauthorized) {
    content = (
      <section className="saved-searches__guest mx-auto w-full max-w-sm py-4">
        <OpenInTelegram />
      </section>
    );
  } else if (loading) {
    content = (
      <ul className="saved-searches__list flex flex-col gap-4">
        {Array.from({ length: SKELETON_COUNT }, (_, index) => (
          <li key={index}>
            <SavedSearchSkeleton />
          </li>
        ))}
      </ul>
    );
  } else if (error) {
    content = <ErrorState onRetry={reload} />;
  } else if (searches.length === 0) {
    content = (
      <EmptyState icon="🔔" title={st.empty_title}>
        <Link
          to="/search"
          className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]"
        >
          {st.to_search}
        </Link>
      </EmptyState>
    );
  } else {
    content = (
      <ul className="saved-searches__list flex flex-col gap-4">
        {searches.map((search) => (
          <li key={search.id}>
            <SavedSearchCard
              search={search}
              districtName={districtName(search)}
              cityNames={cityNames}
              onOpen={() => markSeen(search.id)}
              onToggleNotify={() => void toggleNotify(search.id)}
              onRename={() => setDialog({ kind: 'rename', id: search.id })}
              onDelete={() => setDialog({ kind: 'delete', id: search.id })}
            />
          </li>
        ))}
      </ul>
    );
  }

  return (
    <section
      className="saved-searches mx-auto flex w-full max-w-2xl flex-col gap-6 py-2 sm:py-4"
      aria-labelledby="saved-searches-title"
      aria-busy={loading}
    >
      <header className="saved-searches__header flex items-baseline justify-between gap-3">
        <h1 id="saved-searches-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
          {st.heading}
        </h1>
        {!unauthorized && !loading && searches.length > 0 && (
          <span className="text-sm text-[var(--text-secondary)]">
            {fill(st.count, searches.length)}
          </span>
        )}
      </header>

      {content}

      <RenameSearchModal
        open={dialog?.kind === 'rename'}
        initialName={dialogTitle}
        busy={busy}
        onSubmit={(name) => void submitRename(name)}
        onClose={closeDialog}
      />
      <ConfirmDialog
        open={dialog?.kind === 'delete'}
        title={st.delete_title}
        text={fill(st.delete_text, dialogTitle)}
        confirmLabel={st.delete}
        danger
        busy={busy}
        onConfirm={() => void confirmDelete()}
        onClose={closeDialog}
      />
    </section>
  );
}
