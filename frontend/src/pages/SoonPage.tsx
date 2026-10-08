import { Link } from 'react-router-dom';
import Icon from '../components/Icon';
import type { IconName } from '../components/Icon';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { useI18n } from '../providers/I18nProvider';

/** Разделы главного меню, у которых ещё нет своей страницы */
export type SoonFeature = 'daily' | 'smart' | 'owner' | 'invite';

const ICONS: Record<SoonFeature, IconName> = {
  daily: 'bed',
  smart: 'sparkles',
  owner: 'home_plus',
  invite: 'gift',
};

interface SoonPageProps {
  feature: SoonFeature;
}

/** Заглушка «Скоро»: меню полное сразу, раздел появится в своей задаче */
export default function SoonPage({ feature }: SoonPageProps) {
  const { t } = useI18n();
  const title = t.hub.tiles[feature].title;

  useDocumentTitle(`${title} — bina.ai`);
  useTelegramBackButton('/');

  return (
    <section
      className="soon mx-auto flex w-full max-w-sm flex-col items-center gap-4 py-12 text-center"
      aria-labelledby="soon-title"
    >
      <span className="soon__icon inline-grid size-24 place-items-center rounded-full bg-[var(--surface)] text-[var(--text-primary)] shadow-[var(--shadow-md)]">
        <Icon name={ICONS[feature]} className="size-11 stroke-[1.5]" />
      </span>
      <p className="soon__badge inline-flex items-center gap-1.5 rounded-full bg-[var(--warning-bg)] px-3 py-1 text-xs font-semibold text-[var(--warning-text)]">
        <Icon name="clock" className="size-3.5" />
        {t.soon.badge}
      </p>
      <h1 id="soon-title" className="text-2xl font-bold tracking-tight">
        {title}
      </h1>
      <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{t.soon.text}</p>
      <Link
        to="/"
        className="mt-2 inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]"
      >
        {t.common.to_home}
      </Link>
    </section>
  );
}
