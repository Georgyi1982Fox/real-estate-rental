import { useId } from 'react';
import { Link } from 'react-router-dom';
import type { SavedSearch } from '../api/types';
import { fill } from '../lib/format';
import { describeFilters, filtersToQuery } from '../lib/searchFilters';
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
  /** Переход на главную с фильтрами поиска — новые квартиры считаются просмотренными */
  onOpen: () => void;
  onToggleNotify: () => void;
  onRename: () => void;
  onDelete: () => void;
}

/** Карточка сохранённого поиска: название, фильтры словами, «+N новых», уведомления, действия */
export default function SavedSearchCard({
  search,
  districtName,
  onOpen,
  onToggleNotify,
  onRename,
  onDelete,
}: SavedSearchCardProps) {
  const { t } = useI18n();
  const st = t.searches;
  const titleId = useId();
  const description = describeFilters(search.filters, districtName, st);
  // Без своего названия (mock) заголовком служат сами фильтры
  const title = search.name.trim() || description;
  // Название, которое сервер собрал из фильтров, повторно строкой фильтров не дублируем
  const showDescription = normalize(title) !== normalize(description);
  const query = filtersToQuery(search.filters);

  return (
    <article
      className="saved-search flex flex-col divide-y divide-[var(--border)] overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)]"
      aria-labelledby={titleId}
    >
      <Link
        to={query ? `/?${query}` : '/'}
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
