import { useShareInvite } from '../hooks/useShareInvite';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import SignLink from './SignLink';
import TelegramIcon from './TelegramIcon';

interface SigningSentProps {
  /** Ссылка на бота: открыть документ и подписать (её же пересылают второй стороне) */
  inviteUrl: string;
  /** Бот прислал документ в чат; false — документ сохранён, но написать человеку бот не смог */
  sent: boolean;
  /** «Изменить анкету» — вернуться к форме */
  editLabel: string;
  onEdit: () => void;
}

/**
 * Документ отправлен на подпись (delivery: sign): «Подписать сейчас» — в чат с ботом,
 * «Переслать ссылку» — второй стороне (в браузере ссылка копируется)
 */
export default function SigningSent({ inviteUrl, sent, editLabel, onEdit }: SigningSentProps) {
  const { t } = useI18n();
  const st = t.signing;
  const shareInvite = useShareInvite();

  return (
    <section
      className="signing-sent flex flex-col items-center gap-4 py-2 text-center"
      role="status"
    >
      <span className="signing-sent__icon inline-grid size-14 place-items-center rounded-full bg-[var(--success-bg)] text-[var(--success-text)]">
        <Icon name="signature" className="size-7" />
      </span>
      <h3 className="signing-sent__title text-lg font-semibold">{st.sent_title}</h3>
      <p className="signing-sent__text m-0 break-words text-sm text-[var(--text-secondary)]">
        {sent ? st.sent_text : st.not_sent_text}
      </p>
      <SignLink url={inviteUrl} className="telegram-button">
        <TelegramIcon />
        {st.sign_now}
      </SignLink>
      <button
        type="button"
        className="signing-sent__forward inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-hover)] active:scale-[.98]"
        onClick={() => void shareInvite(inviteUrl)}
      >
        <Icon name="forward" className="size-5" />
        {st.forward}
      </button>
      <button
        type="button"
        className="signing-sent__edit inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] px-4 py-2.5 text-sm font-semibold text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
        onClick={onEdit}
      >
        {editLabel}
      </button>
    </section>
  );
}
