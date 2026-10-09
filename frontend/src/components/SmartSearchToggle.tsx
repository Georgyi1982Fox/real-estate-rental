import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

interface SmartSearchToggleProps {
  checked: boolean;
  onChange: (next: boolean) => void;
}

/** Переключатель «По смыслу»: включён — результаты идут в порядке близости к тексту поиска */
export default function SmartSearchToggle({ checked, onChange }: SmartSearchToggleProps) {
  const { t } = useI18n();

  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      className={`smart-toggle inline-flex min-h-11 max-w-full items-center gap-2 self-start rounded-full border py-1.5 pl-3.5 pr-2 text-sm font-semibold shadow-[var(--shadow-sm)] transition-colors duration-200 active:scale-[.98] ${
        checked
          ? 'border-[var(--primary)] bg-[var(--surface)] text-[var(--text-primary)]'
          : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
      }`}
      onClick={() => {
        haptic('selection');
        onChange(!checked);
      }}
    >
      <Icon name="brain" className="smart-toggle__icon size-4 shrink-0" />
      <span className="smart-toggle__label min-w-0 break-words text-left">
        {t.home.smart_search}
      </span>
      <span
        className={`smart-toggle__track flex h-6 w-10 shrink-0 items-center rounded-full p-0.5 transition-colors duration-200 ${
          checked ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'
        }`}
        aria-hidden="true"
      >
        <span
          className={`smart-toggle__thumb size-5 rounded-full bg-white shadow-[var(--shadow-sm)] transition-transform duration-200 ${
            checked ? 'translate-x-4' : ''
          }`}
        />
      </span>
    </button>
  );
}
