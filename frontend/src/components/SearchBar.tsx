import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent, ReactNode } from 'react';
import type { District } from '../api/types';
import { QUERY_MAX, SUGGEST_MIN_CHARS, suggestDistricts } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import SearchSuggestions, { suggestionId } from './SearchSuggestions';

interface SearchBarProps {
  /** Применённый текст поиска (q из адреса) — с него начинается поле */
  query: string;
  districts: District[];
  /** Районы, уже выбранные в фильтре: в подсказках их нет */
  selectedDistricts: string[];
  /** Поиск по словам; пустая строка — убрать поиск */
  onSearch: (text: string) => void;
  /** Выбран район из подсказок */
  onSelectDistrict: (id: string) => void;
  /** Кнопки рядом с «Найти», например «Фильтры» */
  children?: ReactNode;
}

/** Ничего не выбрано: Enter ищет по введённому тексту */
const NO_OPTION = -1;

/** Строка поиска по словам с подсказками районов (combobox) */
export default function SearchBar({
  query,
  districts,
  selectedDistricts,
  onSearch,
  onSelectDistrict,
  children,
}: SearchBarProps) {
  const { lang, t } = useI18n();
  const ht = t.home;
  const listId = useId();
  const fieldRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState(query);
  const [appliedQuery, setAppliedQuery] = useState(query);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(NO_OPTION);

  // q в адресе изменился (поиск, сброс, «Назад») — поле показывает его
  if (query !== appliedQuery) {
    setAppliedQuery(query);
    setText(query);
  }

  const needle = text.trim();
  const expanded = open && needle.length >= SUGGEST_MIN_CHARS;
  const suggestions = expanded ? suggestDistricts(districts, needle, lang, selectedDistricts) : [];
  // Районы + строка «Искать «текст»»
  const optionCount = suggestions.length + 1;

  const close = () => {
    setOpen(false);
    setActive(NO_OPTION);
  };

  // Клик или касание вне поля закрывает список
  useEffect(() => {
    if (!expanded) return;
    const onPointerDown = (event: PointerEvent) => {
      if (event.target instanceof Node && !fieldRef.current?.contains(event.target)) {
        setOpen(false);
        setActive(NO_OPTION);
      }
    };
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [expanded]);

  const search = () => {
    haptic('light');
    close();
    setText(needle);
    onSearch(needle);
    // На телефоне прячем клавиатуру, чтобы были видны результаты
    if (window.matchMedia('(pointer: coarse)').matches) inputRef.current?.blur();
  };

  const selectDistrict = (id: string) => {
    haptic('light');
    close();
    setText('');
    onSelectDistrict(id);
  };

  const clear = () => {
    haptic('light');
    close();
    setText('');
    if (query) onSearch('');
    inputRef.current?.focus();
  };

  const applyOption = (index: number) => {
    const district = suggestions[index];
    if (district) selectDistrict(district.id);
    else search();
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    search();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    // Enter при наборе через IME подтверждает слово, а не поиск
    if (event.nativeEvent.isComposing) return;
    switch (event.key) {
      case 'ArrowDown':
      case 'ArrowUp': {
        if (needle.length < SUGGEST_MIN_CHARS) return;
        event.preventDefault();
        if (!expanded) {
          setOpen(true);
          setActive(NO_OPTION);
          return;
        }
        const step = event.key === 'ArrowDown' ? 1 : -1;
        // По кругу; из «ничего не выбрано» ↓ ведёт на первую строку, ↑ — на последнюю
        const from = active === NO_OPTION && step < 0 ? 0 : active;
        setActive((from + step + optionCount) % optionCount);
        return;
      }
      case 'Enter':
        if (expanded && active !== NO_OPTION) {
          event.preventDefault();
          applyOption(active);
        }
        return;
      case 'Escape':
        if (expanded) {
          event.preventDefault();
          close();
        }
        return;
      default:
    }
  };

  return (
    <search className="search-bar" aria-label={ht.search_label}>
      <form className="search-bar__form flex flex-col gap-3 sm:flex-row" onSubmit={onSubmit}>
        <label className="sr-only" htmlFor="search-input">
          {ht.search_label}
        </label>
        <div
          ref={fieldRef}
          className="search-bar__field relative min-w-0 flex-1"
          onBlur={(event) => {
            // Фокус ушёл из поля и списка (Tab) — список закрывается
            if (!event.currentTarget.contains(event.relatedTarget)) close();
          }}
        >
          <span className="pointer-events-none absolute inset-y-0 left-3 grid place-items-center text-[var(--text-secondary)]">
            <Icon name="search" className="size-5" />
          </span>
          <input
            ref={inputRef}
            id="search-input"
            type="text"
            inputMode="search"
            enterKeyHint="search"
            name="q"
            value={text}
            maxLength={QUERY_MAX}
            placeholder={ht.search_placeholder}
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            role="combobox"
            aria-expanded={expanded}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={
              expanded && active !== NO_OPTION ? suggestionId(listId, active) : undefined
            }
            className="search-bar__input w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] py-3 pl-10 pr-11 text-sm text-[var(--text-primary)] shadow-[var(--shadow-sm)] placeholder:text-[var(--text-secondary)]"
            onChange={(event) => {
              setText(event.target.value);
              setOpen(true);
              setActive(NO_OPTION);
            }}
            onKeyDown={onKeyDown}
          />
          {text && (
            <button
              type="button"
              className="search-bar__clear absolute inset-y-0 right-1 my-auto grid size-9 place-items-center rounded-full text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] active:scale-[.95]"
              aria-label={ht.search_clear}
              onClick={clear}
            >
              <Icon name="close" className="size-4" />
            </button>
          )}
          {expanded && (
            <SearchSuggestions
              id={listId}
              text={needle}
              districts={suggestions}
              active={active}
              onActiveChange={setActive}
              onSelectDistrict={selectDistrict}
              onSearch={search}
            />
          )}
        </div>
        <div className="search-bar__actions flex gap-3">
          <button
            type="submit"
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-3 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] sm:flex-none"
          >
            {ht.search_button}
          </button>
          {children}
        </div>
      </form>
    </search>
  );
}
