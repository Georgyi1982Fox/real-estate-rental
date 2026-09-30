import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

/** Жёлтый значок ⚠️ в углу фото карточки: у объявления есть признаки мошенничества */
export default function FraudBadge() {
  const { t } = useI18n();

  return (
    // z-10 — поверх «растянутой» ссылки карточки, иначе подсказка title не появится
    <span
      className="fraud-badge absolute left-3 top-4 z-10 inline-flex size-9 items-center justify-center rounded-full border border-white/60 bg-[var(--accent)] text-[var(--warning-ink)] shadow-[var(--shadow-md)]"
      role="img"
      aria-label={t.card.fraud}
      title={t.card.fraud}
    >
      <Icon name="alert" className="size-5" />
    </span>
  );
}
