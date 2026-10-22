import { Link, useMatch } from 'react-router-dom';
import { useReferralBanner } from '../hooks/useReferral';
import { fill } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

/**
 * «Вам скидка N% на первый Premium» — после запуска по ссылке друга (FRONTEND-029).
 * Видна на всех страницах, пока её не закрыли; на экране Premium не нужна — там цены со скидкой
 */
export default function ReferralBanner() {
  const { t } = useI18n();
  const rt = t.referral;
  const { discount, hide } = useReferralBanner();
  const onPremium = useMatch('/premium') !== null;

  if (discount <= 0 || onPremium) return null;

  return (
    <aside
      className="referral-banner mb-4 flex items-center gap-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-3 shadow-[var(--shadow-sm)]"
      aria-label={rt.banner_label}
    >
      <span className="inline-grid size-10 shrink-0 place-items-center rounded-xl bg-[var(--tone-benefit)] text-[var(--surface)]">
        <Icon name="gift" className="size-5" />
      </span>
      <Link
        to="/premium"
        className="referral-banner__link min-w-0 flex-1 text-sm font-semibold leading-snug hover:underline"
        onClick={() => haptic('light')}
      >
        {fill(rt.banner, discount)}
      </Link>
      <button
        type="button"
        className="referral-banner__close inline-grid size-9 shrink-0 place-items-center rounded-full text-[var(--text-secondary)] hover:bg-[var(--surface-hover)]"
        aria-label={t.common.close}
        onClick={() => {
          haptic('light');
          hide();
        }}
      >
        <Icon name="close" className="size-4" />
      </button>
    </aside>
  );
}
