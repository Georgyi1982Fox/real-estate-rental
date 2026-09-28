import { useId } from 'react';
import type { ReactNode } from 'react';
import { BOT_URL, LOGO_URL } from '../lib/config';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import TelegramIcon from './TelegramIcon';

interface OpenInTelegramProps {
  /** Дополнительные способы входа под кнопкой Telegram (Google, email на /auth) */
  children?: ReactNode;
  /** Внутри модалки: без рамки карточки, заголовок h3 (у модалки свой h2) */
  plain?: boolean;
}

/**
 * Карточка «нужен Telegram»: в браузере — ссылка на бота,
 * в Telegram после «Выйти» — кнопка «Войти через Telegram».
 */
export default function OpenInTelegram({ children, plain = false }: OpenInTelegramProps) {
  const { t } = useI18n();
  const { isInTelegram, signInWithTelegram } = useAuth();
  const titleId = useId();
  const Heading = plain ? 'h3' : 'h1';

  return (
    <article
      className={
        plain
          ? 'open-in-telegram open-in-telegram--plain flex flex-col gap-5'
          : 'open-in-telegram flex flex-col gap-5 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow-md)]'
      }
      aria-labelledby={titleId}
    >
      <header className="open-in-telegram__intro flex flex-col items-center gap-3 text-center">
        <img
          className="open-in-telegram__logo medallion medallion--logo size-16 rounded-full"
          src={LOGO_URL}
          alt=""
          width={64}
          height={64}
        />
        <Heading id={titleId} className="text-2xl font-bold tracking-tight">
          {isInTelegram ? t.auth.signed_out_title : t.auth.open_title}
        </Heading>
        <p className="text-sm text-[var(--text-secondary)]">
          {isInTelegram ? t.auth.signed_out_text : t.auth.open_text}
        </p>
      </header>
      {isInTelegram ? (
        <button
          type="button"
          className="telegram-button"
          onClick={() => {
            haptic('light');
            signInWithTelegram();
          }}
        >
          <TelegramIcon />
          {t.auth.sign_in_telegram}
        </button>
      ) : (
        <a className="telegram-button" href={BOT_URL} target="_blank" rel="noopener noreferrer">
          <TelegramIcon />
          {t.auth.open_in_telegram}
        </a>
      )}
      {children}
    </article>
  );
}
