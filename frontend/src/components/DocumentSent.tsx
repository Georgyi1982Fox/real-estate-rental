import { BOT_URL } from '../lib/config';
import { haptic, isInTelegram, openBotChat } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import TelegramIcon from './TelegramIcon';

interface DocumentSentProps {
  title: string;
  text: string;
  /** «Изменить анкету» — вернуться к форме и запросить документ заново */
  editLabel: string;
  onEdit: () => void;
}

/**
 * Документ (договор, акт приёмки) ушёл в чат с ботом: подтверждение и кнопка «Открыть чат».
 * В Telegram она открывает чат и закрывает мини-апп, в браузере — ссылка на бота
 */
export default function DocumentSent({ title, text, editLabel, onEdit }: DocumentSentProps) {
  const { t } = useI18n();

  return (
    <section
      className="document-sent flex flex-col items-center gap-4 py-2 text-center"
      role="status"
    >
      <span className="document-sent__icon inline-grid size-14 place-items-center rounded-full bg-[var(--success-bg)] text-[var(--success-text)]">
        <Icon name="check" className="size-7" />
      </span>
      <h3 className="document-sent__title text-lg font-semibold">{title}</h3>
      <p className="document-sent__text m-0 break-words text-sm text-[var(--text-secondary)]">
        {text}
      </p>
      {isInTelegram() ? (
        <button
          type="button"
          className="telegram-button"
          onClick={() => {
            haptic('light');
            openBotChat(BOT_URL);
          }}
        >
          <TelegramIcon />
          {t.contract.open_chat}
        </button>
      ) : (
        <a className="telegram-button" href={BOT_URL} target="_blank" rel="noopener noreferrer">
          <TelegramIcon />
          {t.contract.open_chat}
        </a>
      )}
      <button
        type="button"
        className="document-sent__edit inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] px-4 py-2.5 text-sm font-semibold text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
        onClick={onEdit}
      >
        {editLabel}
      </button>
    </section>
  );
}
