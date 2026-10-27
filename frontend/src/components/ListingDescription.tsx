import { useLayoutEffect, useRef, useState } from 'react';
import { useI18n } from '../providers/I18nProvider';

interface ListingDescriptionProps {
  text: string;
  /** Текста на языке зрителя ещё нет — AI переводит: вместо чужого языка — заглушка */
  pending?: boolean;
}

/** Длинный текст сворачиваем до 5 строк; кнопка появляется только если текст реально обрезан */
export default function ListingDescription({ text, pending = false }: ListingDescriptionProps) {
  const { t } = useI18n();
  const lt = t.listing;
  const textRef = useRef<HTMLParagraphElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [clamped, setClamped] = useState(false);

  useLayoutEffect(() => {
    const element = textRef.current;
    if (!element || expanded) return;
    const measure = () => setClamped(element.scrollHeight > element.clientHeight + 1);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [text, expanded]);

  return (
    <section
      className="listing-description space-y-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5"
      aria-labelledby="listing-description-title"
    >
      <h2 id="listing-description-title" className="text-lg font-semibold">
        {lt.description}
      </h2>
      {pending ? (
        <div className="listing-description__pending space-y-2" role="status">
          <p className="m-0 text-sm text-[var(--text-secondary)]">{lt.translating}</p>
          <div className="space-y-2" aria-hidden="true">
            <div className="h-3.5 w-full animate-pulse rounded bg-[var(--surface-hover)]" />
            <div className="h-3.5 w-11/12 animate-pulse rounded bg-[var(--surface-hover)]" />
            <div className="h-3.5 w-3/5 animate-pulse rounded bg-[var(--surface-hover)]" />
          </div>
        </div>
      ) : text ? (
        <>
          {/* pre-line сохраняет переносы строк автора; больше одной пустой строки подряд не оставляем */}
          <p
            id="listing-description-text"
            ref={textRef}
            className={`listing-description__text whitespace-pre-line break-words text-sm leading-relaxed text-[var(--text-primary)] sm:text-base ${expanded ? '' : 'line-clamp-5'}`}
          >
            {text.replace(/\r\n?/g, '\n').replace(/\n{3,}/g, '\n\n')}
          </p>
          {(clamped || expanded) && (
            <button
              type="button"
              className="text-sm font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)]"
              aria-controls="listing-description-text"
              aria-expanded={expanded}
              onClick={() => setExpanded((value) => !value)}
            >
              {expanded ? lt.read_less : lt.read_more}
            </button>
          )}
        </>
      ) : (
        <p className="text-sm text-[var(--text-secondary)]">{lt.no_description}</p>
      )}
    </section>
  );
}
