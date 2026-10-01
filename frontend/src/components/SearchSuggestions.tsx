import type { ReactNode } from 'react';
import type { District } from '../api/types';
import { fill, tr } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

interface SearchSuggestionsProps {
  /** id списка: на него ссылается aria-controls поля */
  id: string;
  /** Введённый текст — подсвечивается в названиях и подставляется в «Искать «…»» */
  text: string;
  /** Подходящие районы; после них всегда идёт строка обычного поиска */
  districts: District[];
  /** Номер выбранной строки (стрелки, наведение); -1 — ничего не выбрано */
  active: number;
  onActiveChange: (index: number) => void;
  onSelectDistrict: (id: string) => void;
  onSearch: () => void;
}

/** id строки списка — для aria-activedescendant поля */
export function suggestionId(listId: string, index: number): string {
  return `${listId}-option-${index}`;
}

/** Название района с выделенным совпадением: «<mark>Саб</mark>уртало» */
function highlight(name: string, text: string): ReactNode {
  const start = name.toLocaleLowerCase().indexOf(text.toLocaleLowerCase());
  // Совпало название на другом языке — подсвечивать нечего
  if (start < 0) return name;
  const end = start + text.length;
  return (
    <>
      {name.slice(0, start)}
      <mark className="search-suggestions__match bg-transparent font-bold text-[var(--text-primary)]">
        {name.slice(start, end)}
      </mark>
      {name.slice(end)}
    </>
  );
}

const OPTION_CLASS =
  'search-suggestions__option flex min-h-11 cursor-pointer items-center gap-3 px-4 py-2.5 text-sm transition-colors duration-200';

/** Выпадающий список под строкой поиска: районы + «Искать «текст»» */
export default function SearchSuggestions({
  id,
  text,
  districts,
  active,
  onActiveChange,
  onSelectDistrict,
  onSearch,
}: SearchSuggestionsProps) {
  const { lang, t } = useI18n();
  const ht = t.home;
  const searchIndex = districts.length;
  const optionClass = (index: number) =>
    `${OPTION_CLASS} ${index === active ? 'bg-[var(--surface-hover)]' : ''}`;

  return (
    <ul
      id={id}
      role="listbox"
      aria-label={ht.search_suggestions}
      className="search-suggestions absolute inset-x-0 top-full z-20 mt-2 max-h-80 overflow-y-auto rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] py-1 shadow-[var(--shadow-lg)]"
      // Фокус остаётся в поле: иначе список закроется раньше, чем сработает клик
      onMouseDown={(event) => event.preventDefault()}
    >
      {districts.map((district, index) => (
        <li
          key={district.id}
          id={suggestionId(id, index)}
          role="option"
          aria-selected={index === active}
          className={`${optionClass(index)} text-[var(--text-secondary)]`}
          onMouseMove={() => onActiveChange(index)}
          onClick={() => onSelectDistrict(district.id)}
        >
          <Icon name="pin" className="size-4 shrink-0" />
          <span className="min-w-0 truncate">{highlight(tr(district.name, lang), text)}</span>
        </li>
      ))}
      <li
        id={suggestionId(id, searchIndex)}
        role="option"
        aria-selected={searchIndex === active}
        className={`${optionClass(searchIndex)} font-medium text-[var(--text-primary)] ${
          districts.length > 0 ? 'border-t border-[var(--border)]' : ''
        }`}
        onMouseMove={() => onActiveChange(searchIndex)}
        onClick={onSearch}
      >
        <Icon name="search" className="size-4 shrink-0 text-[var(--text-secondary)]" />
        <span className="min-w-0 truncate">{fill(ht.search_for, text)}</span>
      </li>
    </ul>
  );
}
