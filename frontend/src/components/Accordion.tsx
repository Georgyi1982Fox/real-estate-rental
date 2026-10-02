import Icon from './Icon';

export interface AccordionItem {
  title: string;
  /** Обычный текст; переводы строк сохраняются как абзацы */
  text: string;
}

interface AccordionProps {
  items: AccordionItem[];
  /** Какой пункт открыт сразу; по умолчанию все закрыты */
  openIndex?: number;
}

/** Список раскрывающихся пунктов на нативном <details>: работает с клавиатуры без JS */
export default function Accordion({ items, openIndex }: AccordionProps) {
  return (
    <ul className="accordion divide-y divide-[var(--border)] overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)]">
      {items.map((item, index) => (
        <li key={`${index}-${item.title}`} className="accordion__item">
          <details className="group" open={index === openIndex}>
            <summary className="accordion__summary flex min-h-12 cursor-pointer list-none items-center gap-3 px-4 py-3 text-sm font-semibold hover:bg-[var(--surface-hover)] focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-[var(--primary)] [&::-webkit-details-marker]:hidden">
              <span className="min-w-0 flex-1">{item.title}</span>
              <Icon
                name="chevron"
                className="size-4 text-[var(--text-secondary)] transition-transform duration-200 group-open:rotate-90"
              />
            </summary>
            <p className="accordion__text whitespace-pre-line px-4 pb-4 text-sm leading-relaxed text-[var(--text-secondary)]">
              {item.text}
            </p>
          </details>
        </li>
      ))}
    </ul>
  );
}
