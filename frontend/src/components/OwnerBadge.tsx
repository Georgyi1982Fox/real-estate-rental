import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

/** Зелёный значок «Собственник» рядом с ценой в карточке: объявление без посредников */
export default function OwnerBadge() {
  const { t } = useI18n();

  return (
    <span className="owner-badge inline-flex items-center gap-1 rounded-full bg-[var(--success-bg)] px-2 py-0.5 text-xs font-semibold leading-5 text-[var(--success-text)]">
      <Icon name="check" className="size-3.5" />
      {t.card.owner}
    </span>
  );
}
