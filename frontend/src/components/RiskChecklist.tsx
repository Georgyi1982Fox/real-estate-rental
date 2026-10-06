import Icon from './Icon';

interface RiskChecklistProps {
  /** Советы с бэкенда, уже на языке пользователя */
  items: string[];
  label: string;
}

/** Список советов галочками: «Что проверить до встречи», «Как безопасно снять квартиру» */
export default function RiskChecklist({ items, label }: RiskChecklistProps) {
  return (
    <ul className="risk-checklist m-0 list-none space-y-2 p-0" aria-label={label}>
      {items.map((text, index) => (
        <li key={`${index}-${text}`} className="risk-checklist__item flex gap-2">
          <Icon name="check" className="mt-0.5 size-4" />
          <span className="min-w-0 break-words">{text}</span>
        </li>
      ))}
    </ul>
  );
}
