import { useCallback, useId, useState } from 'react';
import type { City } from '../api/types';
import { DEFAULT_CITY } from '../hooks/useCity';
import { fill, tr } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import ErrorState from './ErrorState';
import Icon from './Icon';
import Modal from './Modal';

/** Если городов больше, над списком появляется поиск по названию */
const SEARCH_FROM = 8;
const LANGS = ['ka', 'ru', 'en'] as const;

const OPTION_CLASS =
  'city-picker__option flex min-h-12 w-full items-center justify-between gap-3 rounded-[var(--radius-md)] px-3 py-2.5 text-left text-sm transition-colors duration-200 hover:bg-[var(--surface-hover)] active:scale-[.99]';

interface CityPickerProps {
  /** Код выбранного города; undefined — «Вся Грузия» */
  city: string | undefined;
  /** Города из GET /api/cities — только те, где есть объявления */
  cities: City[];
  loading: boolean;
  /** Список городов не загрузился */
  failed: boolean;
  onRetry: () => void;
  onChange: (city: string | undefined) => void;
}

/** Кнопка «📍 Тбилиси ▾» и окно со списком городов; первый пункт — «Вся Грузия» */
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
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const close = useCallback(() => setOpen(false), []);

  const current = cities.find((item) => item.code === city);
  // Пока список грузится, названия ещё нет: для города по умолчанию оно есть в словаре
  let label = ct.all;
  if (current) label = tr(current.name, lang);
  else if (city) label = city === DEFAULT_CITY ? ct.default_name : city;

  // Ищем по названию на любом языке: «batumi» найдёт «Батуми»
  const needle = query.trim().toLocaleLowerCase();
  const visible = needle
    ? cities.filter((item) =>
        LANGS.some((key) => tr(item.name, key).toLocaleLowerCase().includes(needle)),
      )
    : cities;

  const select = (next: string | undefined) => {
    haptic('selection');
    setOpen(false);
    if (next !== city) onChange(next);
  };

  const option = (code: string | undefined, name: string) => {
    const active = code === city;
    return (
      <li key={code ?? ''}>
        <button
          type="button"
          className={`${OPTION_CLASS} text-[var(--text-primary)] ${active ? 'font-semibold' : ''}`}
          aria-current={active ? 'true' : undefined}
          onClick={() => select(code)}
        >
          <span className="min-w-0 break-words">{name}</span>
          {active && <Icon name="check" className="size-5 shrink-0 text-[var(--secondary)]" />}
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
          setOpen(true);
        }}
      >
        <Icon name="pin" className="size-4 shrink-0 text-[var(--text-secondary)]" />
        <span className="truncate">{label}</span>
        <Icon name="chevron" className="size-4 shrink-0 rotate-90 text-[var(--text-secondary)]" />
      </button>

      <Modal open={open} title={ct.title} onClose={close}>
        <div className="city-picker__list flex flex-col gap-3">
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
