import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

const BADGE_CLASS =
  'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold leading-5';

interface PromotionBadgesProps {
  /** Оплачен «Топ»: объект вверху поиска */
  promoted: boolean;
  /** Bina.ai проверил хозяина */
  verified: boolean;
  /** «⭐ Premium-объявление» агентства */
  premium?: boolean;
  className?: string;
}

/** Значки «Топ», «⭐ Premium» (оранжевые) и «Проверено» (зелёный); ни одного — ничего не рисуем */
export default function PromotionBadges({
  promoted,
  verified,
  premium = false,
  className = '',
}: PromotionBadgesProps) {
  const { t } = useI18n();

  if (!promoted && !verified && !premium) return null;

  return (
    <span className={`promotion-badges inline-flex flex-wrap items-center gap-1.5 ${className}`}>
      {promoted && (
        <span
          className={`promotion-badges__top ${BADGE_CLASS} bg-[var(--promo-bg)] text-[var(--promo-text)]`}
        >
          <Icon name="flame" className="size-3.5" />
          {t.hotels.top}
        </span>
      )}
      {premium && (
        <span
          className={`promotion-badges__premium ${BADGE_CLASS} bg-[var(--promo-bg)] text-[var(--promo-text)]`}
        >
          <Icon name="star" className="size-3.5" />
          {t.agency.premium_badge}
        </span>
      )}
      {verified && (
        <span
          className={`promotion-badges__verified ${BADGE_CLASS} bg-[var(--success-bg)] text-[var(--success-text)]`}
        >
          <Icon name="badge_check" className="size-3.5" />
          {t.hotels.verified}
        </span>
      )}
    </span>
  );
}
