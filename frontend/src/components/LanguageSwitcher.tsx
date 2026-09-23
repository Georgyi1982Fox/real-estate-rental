import { useEffect, useRef, useState } from 'react';
import { LANGUAGES } from '../i18n/strings';
import { useI18n } from '../providers/I18nProvider';

export default function LanguageSwitcher() {
  const { lang, setLang, t } = useI18n();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Закрытие по клику вне меню и по Escape
  useEffect(() => {
    if (!open) return;
    const handlePointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', handlePointer);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('pointerdown', handlePointer);
      document.removeEventListener('keydown', handleKey);
    };
  }, [open]);

  return (
    <div className="header__language relative" ref={rootRef}>
      <button
        type="button"
        className="app-icon-button text-sm font-semibold"
        aria-label={t.header.language}
        aria-haspopup="true"
        aria-controls="language-menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {lang.toUpperCase()}
      </button>
      <ul
        id="language-menu"
        className={`header__language-menu absolute right-0 top-full z-30 mt-2 min-w-40 overflow-hidden rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] py-1 shadow-[var(--shadow-lg)] transition-opacity duration-200 ${open ? 'opacity-100' : 'pointer-events-none invisible opacity-0'}`}
      >
        {LANGUAGES.map(({ code, label }) => {
          const active = code === lang;
          return (
            <li key={code}>
              <button
                type="button"
                lang={code}
                aria-current={active ? 'true' : undefined}
                className={`flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left text-sm transition-colors hover:bg-[var(--surface-hover)] ${active ? 'font-semibold text-[var(--primary)]' : 'text-[var(--text-primary)]'}`}
                onClick={() => {
                  setLang(code);
                  setOpen(false);
                }}
              >
                <span>{label}</span>
                {active && <span aria-hidden="true">✓</span>}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
