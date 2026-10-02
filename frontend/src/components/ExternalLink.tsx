import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { isInTelegram, openLink } from '../lib/telegram';

interface ExternalLinkProps {
  href: string;
  className?: string;
  children: ReactNode;
}

/** Внешняя ссылка: в Telegram открывается через SDK (openLink), в браузере — в новой вкладке */
export default function ExternalLink({ href, className, children }: ExternalLinkProps) {
  const navigate = useNavigate();

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={className}
      onClick={(event) => {
        // В Telegram внешние ссылки — только через SDK; в браузере работает обычная ссылка
        if (!isInTelegram()) return;
        event.preventDefault();
        openLink(href, (path) => navigate(path));
      }}
    >
      {children}
    </a>
  );
}
