import { useId } from 'react';
import { Link } from 'react-router-dom';
import type { SavedSearch } from '../api/types';
import type { CityNames } from '../hooks/useCity';
import { fill } from '../lib/format';
import {
  ALL_CITIES,
  describeFilters,
  extraFilterChips,
  filtersToQuery,
} from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import Switch from './Switch';

const ACTION_CLASS =
  'saved-search__action inline-flex min-h-11 flex-1 items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium hover:bg-[var(--surface-hover)]';

/** Только буквы и цифры: «Ваке, 2 комн., до 2000 ₾» и «Ваке · 2 комн. · до 2 000 ₾» совпадут */
const normalize = (text: string) => text.replace(/[^\p{L}\p{N}]/gu, '').toLowerCase();

interface SavedSearchCardProps {
  search: SavedSearch;
  /** Районы поиска словами: «Ваке, Сабуртало +1» */
  districtName: string;
  cityNames: CityNames;
  /** Переход на главную с фильтрами поиска — новые квартиры считаются просмотренными */
  onOpen: () => void;
  onToggleNotify: () => void;
  onRename: () => void;
  onDelete: () => void;
}

/**
 * Карточка сохранённого поиска: название, фильтры словами, дополнительные фильтры чипами,
 * «+N новых», уведомления, действия
 */
export default function SavedSearchCard({
  search,
  districtName,
  cityNames,
  onOpen,
  onToggleNotify,
  onRename,
  onDelete,
}: SavedSearchCardProps) {
  const { t, lang } = useI18n();
  const st = t.searches;
  const titleId = useId();
  const chips = extraFilterChips(search.filters, t, lang, cityNames);
  const description = describeFilters(search.filters, districtName, st);
  // Без своего названия (mock) заголовком служат сами фильтры
  const title = search.name.trim() || description;
  // Название, которое сервер собрал из фильтров, повторно строкой фильтров не дублируем
  const showDescription = normalize(title) !== normalize(description);
  // Поиск открывается в своём городе; без города он сохранён по всей Грузии
  const query = filtersToQuery({ ...search.filters, city: search.filters.city ?? ALL_CITIES });

  return (
    <article
      className="saved-search flex flex-col divide-y divide-[var(--border)] overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)]"
      aria-labelledby={titleId}
    >
      <Link
        to={`/search?${query}`}
        className="saved-search__open flex items-start gap-3 p-4 hover:bg-[var(--surface-hover)]"
        onClick={() => {
          haptic('light');
          onOpen();
        }}
      >
        {/* div, а не span: внутри ссылки заголовок, span его содержать не может */}
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <h2 id={titleId} className="saved-search__title text-base font-semibold">
            {title}
          </h2>
          {showDescription && (
            <span className="saved-search__filters text-sm text-[var(--text-secondary)]">
              {description}
            </span>
          )}
          {chips.length > 0 && (
            <ul className="saved-search__chips mt-1 flex list-none flex-wrap gap-1.5 p-0">
              {chips.map((chip) => (
                <li
                  key={chip.key}
                  className="saved-search__chip max-w-full truncate rounded-full bg-[var(--surface-hover)] px-2.5 py-1 text-xs font-medium text-[var(--text-primary)]"
                >
                  {chip.label}
                </li>
              ))}
            </ul>
          )}
        </div>
        {search.new_count > 0 && (
          <span className="saved-search__badge shrink-0 rounded-full bg-[var(--secondary)] px-2.5 py-1 text-xs font-bold text-white">
            {fill(st.new_count, search.new_count)}
          </span>
        )}
        <Icon name="chevron" className="mt-0.5 size-5 text-[var(--text-secondary)]" />
      </Link>

      <Switch label={st.notifications} checked={search.notify} onChange={onToggleNotify} />

      <footer className="saved-search__actions flex divide-x divide-[var(--border)]">
        <button
          type="button"
          className={`${ACTION_CLASS} text-[var(--text-primary)]`}
          aria-haspopup="dialog"
          onClick={() => {
            haptic('light');
            onRename();
          }}
        >
          <Icon name="pencil" className="size-4" />
          {st.rename}
        </button>
        <button
          type="button"
          className={`${ACTION_CLASS} text-[var(--danger)]`}
          aria-haspopup="dialog"
          onClick={() => {
            haptic('light');
            onDelete();
          }}
        >
          <Icon name="trash" className="size-4" />
          {st.delete}
        </button>
      </footer>
    </article>
  );
}
