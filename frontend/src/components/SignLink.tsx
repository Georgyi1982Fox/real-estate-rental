import type { ReactNode } from 'react';
import { haptic, isInTelegram, openBotChat } from '../lib/telegram';

interface SignLinkProps {
  /** Ссылка на бота с документом (invite_url) */
  url: string;
  className: string;
  children: ReactNode;
}

/**
 * «Подписать»: открывает документ в чате с ботом — там кнопка «✍️ Подписать».
 * В Telegram мини-апп закрывается, чтобы не остаться поверх чата; в браузере — ссылка на бота
 */
export default function SignLink({ url, className, children }: SignLinkProps) {
  if (isInTelegram()) {
    return (
      <button
        type="button"
        className={className}
        onClick={() => {
          haptic('light');
          openBotChat(url);
        }}
      >
        {children}
      </button>
    );
  }
  return (
    <a className={className} href={url} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  );
}
