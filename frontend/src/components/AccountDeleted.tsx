import { APP_BASE } from '../lib/config';
import { getWebApp, haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

/**
 * Экран после удаления аккаунта. «Закрыть» в Telegram закрывает мини-апп (при следующем
 * открытии бэкенд заведёт новый профиль), в браузере — перезагружает приложение с нуля
 */
export default function AccountDeleted() {
  const { t } = useI18n();
  const at = t.account;

  const close = () => {
    haptic('light');
    const webApp = getWebApp();
    if (webApp) webApp.close();
    else window.location.assign(APP_BASE);
  };

  return (
    <section
      className="account-deleted flex flex-col items-center gap-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] px-6 py-12 text-center shadow-[var(--shadow-sm)]"
      role="status"
    >
      <span className="grid size-14 place-items-center rounded-full bg-[var(--success-bg)] text-[var(--success-text)]">
        <Icon name="check" className="size-7" />
      </span>
      <h1 className="m-0 text-xl font-semibold text-[var(--text-primary)]">{at.deleted_title}</h1>
      <p className="m-0 max-w-sm text-sm leading-relaxed text-[var(--text-secondary)]">
        {at.deleted_text}
      </p>
      <button
        type="button"
        className="account-deleted__close mt-4 inline-flex min-h-12 w-full max-w-xs items-center justify-center rounded-[var(--radius-lg)] bg-[var(--primary)] px-5 py-3 text-sm font-semibold text-white shadow-[var(--shadow-sm)] hover:bg-[var(--primary-hover)] active:scale-[.98]"
        onClick={close}
      >
        {t.common.close}
      </button>
    </section>
  );
}
