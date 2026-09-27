import { haptic } from '../lib/telegram';

interface SwitchProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

/** Строка настройки с переключателем: нажимается вся строка, для скринридера — role="switch" */
export default function Switch({ label, checked, onChange }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      className="switch flex min-h-12 w-full items-center justify-between gap-4 px-4 py-3 text-left text-sm font-medium hover:bg-[var(--surface-hover)]"
      onClick={() => {
        haptic('selection');
        onChange(!checked);
      }}
    >
      <span className="switch__label min-w-0">{label}</span>
      <span
        className={`switch__track relative inline-flex h-7 w-12 shrink-0 rounded-full transition-colors duration-200 ${checked ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'}`}
        aria-hidden="true"
      >
        <span
          className={`switch__thumb absolute left-0.5 top-0.5 size-6 rounded-full bg-white shadow-[var(--shadow-md)] transition-transform duration-200 ${checked ? 'translate-x-5' : ''}`}
        />
      </span>
    </button>
  );
}
