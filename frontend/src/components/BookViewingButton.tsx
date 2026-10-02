import { useI18n } from '../providers/I18nProvider';
import ExternalLink from './ExternalLink';
import Icon from './Icon';

interface BookViewingButtonProps {
  /** Ссылка на переписку с хозяином в боте: там же запись на просмотр */
  href: string;
}

/** «Записаться на просмотр» — только у объявлений, которые разместил сам хозяин */
export default function BookViewingButton({ href }: BookViewingButtonProps) {
  const { t } = useI18n();

  return (
    <ExternalLink
      href={href}
      className="listing-contact__viewing inline-flex min-h-12 items-center justify-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-center text-sm font-semibold text-[var(--text-primary)] shadow-[var(--shadow-sm)] hover:bg-[var(--surface-hover)] active:scale-[.98]"
    >
      <Icon name="calendar_check" />
      {t.listing.book_viewing}
    </ExternalLink>
  );
}
