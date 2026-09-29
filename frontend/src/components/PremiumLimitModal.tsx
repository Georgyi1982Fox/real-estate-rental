import { Link } from 'react-router-dom';
import { hidePremiumPrompt, usePremiumPrompt } from '../hooks/usePremiumPrompt';
import { fill } from '../lib/format';
import { FREE_LIMITS, PREMIUM_LIMITS } from '../lib/premium';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import Modal from './Modal';

/** Окно «лимит бесплатного тарифа» (ошибка 402) — одно на всё приложение, живёт в Layout */
export default function PremiumLimitModal() {
  const { t } = useI18n();
  const pt = t.premium;
  const reason = usePremiumPrompt();

  const text =
    reason === 'searches'
      ? fill(pt.limit_searches, FREE_LIMITS.searches)
      : fill(pt.limit_favorites, FREE_LIMITS.favorites ?? '');

  return (
    <Modal open={reason !== null} title={pt.limit_title} onClose={hidePremiumPrompt}>
      <section className="premium-limit flex flex-col items-center gap-4 text-center">
        <span className="premium-limit__icon inline-grid size-14 place-items-center rounded-full bg-[var(--accent)]/15 text-[var(--accent)]">
          <Icon name="crown" className="size-7" />
        </span>
        <p className="premium-limit__text text-base font-semibold">{text}</p>
        <p className="premium-limit__hint text-sm text-[var(--text-secondary)]">
          {fill(pt.limit_text, PREMIUM_LIMITS.searches)}
        </p>
        <Link
          to="/premium"
          className="premium-limit__cta inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-3 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]"
          onClick={() => {
            haptic('light');
            hidePremiumPrompt();
          }}
        >
          <Icon name="crown" className="size-4" />
          {pt.get_premium}
        </Link>
      </section>
    </Modal>
  );
}
