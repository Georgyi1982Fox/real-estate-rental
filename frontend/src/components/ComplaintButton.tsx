import { useCallback, useState } from 'react';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import ComplaintModal from './ComplaintModal';
import Icon from './Icon';

interface ComplaintButtonProps {
  /** Куда отправить жалобу: /api/hotels/{id}/complaints, /api/listings/{id}/complaints */
  path: string;
  className?: string;
}

/** Неброская кнопка «🚩 Пожаловаться» и окно жалобы (гостиница, объявление) */
export default function ComplaintButton({ path, className = '' }: ComplaintButtonProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);

  return (
    <>
      <button
        type="button"
        className={`complaint-button inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-md)] px-2 text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] active:scale-[.98] ${className}`}
        aria-haspopup="dialog"
        onClick={() => {
          haptic('light');
          setOpen(true);
        }}
      >
        <Icon name="flag" className="size-4" />
        {t.complaint.button}
      </button>
      <ComplaintModal open={open} onClose={close} path={path} />
    </>
  );
}
