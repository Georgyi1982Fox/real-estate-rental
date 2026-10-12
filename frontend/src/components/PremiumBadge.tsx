import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

/** Пометка «Premium» рядом с заголовком возможности, которая есть только в платном тарифе */
export default function PremiumBadge() {
  const { t } = useI18n();

  return (
    <span className="premium-badge inline-flex items-center gap-1 rounded-full bg-[var(--warning-bg)] px-2 py-0.5 text-xs font-semibold text-[var(--warning-text)]">
      <Icon name="crown" className="size-3.5" />
      {t.premium.premium}
    </span>
  );
}
