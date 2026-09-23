import { useFavorite } from '../hooks/useFavorite';
import { useI18n } from '../providers/I18nProvider';

/** Кнопка «В избранное» со страницы квартиры (у карточки своя, компактная) */
export default function FavoriteButton() {
  const { t } = useI18n();
  const { isFavorite, toggle } = useFavorite();

  return (
    <button
      type="button"
      className="listing-contact__favorite inline-flex min-h-12 items-center justify-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-hover)] active:scale-[.98]"
      aria-label={t.card.favorite}
      aria-pressed={isFavorite}
      onClick={toggle}
    >
      <span
        className={`text-lg leading-none transition-transform duration-200 ${isFavorite ? 'scale-110 text-[var(--danger)]' : 'text-[var(--text-secondary)]'}`}
        aria-hidden="true"
      >
        ♥
      </span>
      <span>{isFavorite ? t.listing.favorite_saved : t.listing.favorite_add}</span>
    </button>
  );
}
