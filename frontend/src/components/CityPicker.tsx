import { useCallback, useId, useState } from 'react';
import type { City } from '../api/types';
import { DEFAULT_CITY } from '../hooks/useCity';
import { fill, tr } from '../lib/format';
import { cityCodes, joinCities } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import ErrorState from './ErrorState';
import Icon from './Icon';
import Modal from './Modal';

/** Если городов больше, над списком появляется поиск по названию */
const SEARCH_FROM = 8;
const LANGS = ['ka', 'ru', 'en'] as const;
/** Столько названий на кнопке, остальные — «+2» */
const NAMES_SHOWN = 2;

const OPTION_CLASS =
  'city-picker__option flex min-h-12 w-full items-center justify-between gap-3 rounded-[var(--radius-md)] px-3 py-2.5 text-left text-sm transition-colors duration-200 hover:bg-[var(--surface-hover)] active:scale-[.99]';

interface CityPickerProps {
  /** Выбранный город или несколько через запятую ('batumi,tbilisi'); undefined — «Вся Грузия» */
  city: string | undefined;
  /** Города из GET /api/cities — только те, где есть объявления */
  cities: City[];
  loading: boolean;
  /** Список городов не загрузился */
  failed: boolean;
  onRetry: () => void;
  onChange: (city: string | undefined) => void;
}

/**
 * Кнопка «📍 Тбилиси ▾» и окно со списком городов: можно отметить несколько (TASK-122) —
 * поиск сразу по всем. Первый пункт — «Вся Грузия» (снимает выбор)
 */
export default function CityPicker({
  city,
  cities,
  loading,
  failed,
  onRetry,
  onChange,
}: CityPickerProps) {
  const { lang, t } = useI18n();
  const ct = t.city;
  const searchId = useId();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  // Отмеченные в окне города; применяются кнопкой «Показать»
  const [picked, setPicked] = useState<string[]>([]);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const close = useCallback(() => setOpen(false), []);

  // Пока список грузится, названий ещё нет: для города по умолчанию оно есть в словаре
  const nameOf = (code: string): string => {
    const found = cities.find((item) => item.code === code);
    if (found) return tr(found.name, lang);
    return code === DEFAULT_CITY ? ct.default_name : code;
  };
  const selected = cityCodes(city);
  const names = selected.map(nameOf).sort(new Intl.Collator(lang).compare);
  let label = ct.all;
  if (names.length > 0) {
    label = names.slice(0, NAMES_SHOWN).join(', ');
    if (names.length > NAMES_SHOWN) label += ` ${fill(ct.more, names.length - NAMES_SHOWN)}`;
  }

  // Ищем по названию на любом языке: «batumi» найдёт «Батуми»
  const needle = query.trim().toLocaleLowerCase();
  const visible = needle
    ? cities.filter((item) =>
        LANGS.some((key) => tr(item.name, key).toLocaleLowerCase().includes(needle)),
      )
    : cities;

  /** Отметить город или снять отметку; «Вся Грузия» снимает все */
  const toggle = (code: string | undefined) => {
    haptic('selection');
    if (code === undefined) {
      setPicked([]);
      return;
    }
    setPicked((current) =>
      current.includes(code) ? current.filter((item) => item !== code) : [...current, code],
    );
  };

  const apply = () => {
    haptic('light');
    setOpen(false);
    const next = joinCities(picked);
    if (next !== joinCities(selected)) onChange(next);
  };

  const option = (code: string | undefined, name: string) => {
    const active = code === undefined ? picked.length === 0 : picked.includes(code);
    return (
      <li key={code ?? ''}>
        <button
          type="button"
          role="checkbox"
          aria-checked={active}
          className={`${OPTION_CLASS} text-[var(--text-primary)] ${active ? 'font-semibold' : ''}`}
          onClick={() => toggle(code)}
        >
          <span className="min-w-0 break-words">{name}</span>
          {/* Квадрат-галочка: видно, что можно отметить несколько */}
          <span
            className={`inline-grid size-6 shrink-0 place-items-center rounded-md border-2 transition-colors ${
              active
                ? 'border-[var(--primary)] bg-[var(--primary)] text-white'
                : 'border-[var(--border)] text-transparent'
            }`}
            aria-hidden="true"
          >
            <Icon name="check" className="size-4 stroke-[3]" />
          </span>
        </button>
      </li>
    );
  };

  return (
    <>
      <button
        type="button"
        className="city-picker inline-flex min-h-11 max-w-full items-center gap-1.5 self-start rounded-full border border-[var(--border)] bg-[var(--surface)] py-2 pl-3 pr-2.5 text-sm font-semibold text-[var(--text-primary)] shadow-[var(--shadow-sm)] transition-colors duration-200 hover:bg-[var(--surface-hover)] active:scale-[.98]"
        aria-haspopup="dialog"
        aria-label={fill(ct.choose, label)}
        onClick={() => {
          haptic('light');
          setQuery('');
          setPicked(selected);
          setOpen(true);
        }}
      >
        <Icon name="pin" className="size-4 shrink-0 text-[var(--text-secondary)]" />
        <span className="truncate">{label}</span>
        <Icon name="chevron" className="size-4 shrink-0 rotate-90 text-[var(--text-secondary)]" />
      </button>

      <Modal
        open={open}
        title={ct.title_many}
        onClose={close}
        footer={
          <button
            type="button"
            className="city-picker__apply inline-flex min-h-12 w-full items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-3 text-sm font-semibold text-white shadow-[var(--shadow-sm)] hover:bg-[var(--primary-hover)] active:scale-[.98]"
            onClick={apply}
          >
            {ct.apply}
            {picked.length > 1 ? ` · ${picked.length}` : ''}
          </button>
        }
      >
        <div className="city-picker__list flex flex-col gap-3">
          <p className="m-0 text-xs text-[var(--text-secondary)]">{ct.hint}</p>
          {cities.length > SEARCH_FROM && (
            <div className="relative">
              <label className="sr-only" htmlFor={searchId}>
                {ct.find}
              </label>
              <span
                className="pointer-events-none absolute inset-y-0 left-3 grid place-items-center text-[var(--text-secondary)]"
                aria-hidden="true"
              >
                <Icon name="search" className="size-4" />
              </span>
              <input
                id={searchId}
                type="search"
                value={query}
                placeholder={ct.find}
                autoComplete="off"
                className="w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] py-2.5 pl-9 pr-3 text-sm text-[var(--text-primary)]"
                onChange={(event) => setQuery(event.target.value)}
              />
            </div>
          )}
          <ul className="flex list-none flex-col gap-1 p-0" aria-busy={loading}>
            {!needle && option(undefined, ct.all)}
            {visible.map((item) => option(item.code, tr(item.name, lang)))}
          </ul>
          {loading && (
            <p className="flex justify-center py-4">
              <span className="spinner" aria-hidden="true" />
            </p>
          )}
          {failed && <ErrorState compact onRetry={onRetry} />}
          {needle && visible.length === 0 && (
            <p className="px-3 text-sm text-[var(--text-secondary)]">{ct.not_found}</p>
          )}
        </div>
      </Modal>
    </>
  );
}
