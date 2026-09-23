import { useLayoutEffect, useRef, useState } from 'react';
import { useI18n } from '../providers/I18nProvider';

interface ListingDescriptionProps {
  text: string;
}

/** Длинный текст сворачиваем до 5 строк; кнопка появляется только если текст реально обрезан */
export default function ListingDescription({ text }: ListingDescriptionProps) {
  const { t } = useI18n();
  const lt = t.listing;
  const textRef = useRef<HTMLDivElement>(null);
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
      {text ? (
        <>
          <div
            id="listing-description-text"
            ref={textRef}
            className={`listing-description__text space-y-3 break-words text-sm leading-relaxed text-[var(--text-primary)] sm:text-base ${expanded ? '' : 'line-clamp-5'}`}
          >
            {text.split('\n\n').map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
          </div>
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
