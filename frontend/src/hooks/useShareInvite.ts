import { useCallback } from 'react';
import { shareInviteUrl } from '../lib/signing';
import { getWebApp, haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';

/**
 * «Переслать ссылку» на подпись второй стороне. В Telegram — окно «Поделиться» (выбор чата),
 * в браузере — копирование; если буфер обмена недоступен, открываем t.me/share в новой вкладке
 */
export function useShareInvite() {
  const { t } = useI18n();
  const showToast = useToast();

  return useCallback(
    /** copiedText — тост после копирования в браузере; по умолчанию — про подпись */
    async (inviteUrl: string, copiedText?: string) => {
      haptic('light');
      const webApp = getWebApp();
      if (webApp) {
        try {
          webApp.openTelegramLink(shareInviteUrl(inviteUrl));
          return;
        } catch {
          // Старый клиент без openTelegramLink — попробуем скопировать
        }
      }
      try {
        await navigator.clipboard.writeText(inviteUrl);
        haptic('success');
        showToast(copiedText ?? t.signing.copied, 'success');
      } catch {
        window.open(shareInviteUrl(inviteUrl), '_blank', 'noopener,noreferrer');
      }
    },
    [showToast, t],
  );
}
