import { useState } from 'react';
import { botSectionUrl } from '../lib/config';
import { deleteAccount, downloadMyData } from '../lib/account';
import { haptic, isInTelegram } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import ConfirmDialog from './ConfirmDialog';
import Icon from './Icon';
import ProfileSection from './ProfileSection';
import SignLink from './SignLink';

const ROW_CLASS =
  'profile-data__row flex min-h-12 w-full items-center gap-3 px-4 py-3 text-left text-sm font-medium hover:bg-[var(--surface-hover)] disabled:opacity-60';

interface ProfileDataProps {
  /** Аккаунт удалён (DELETE /api/me ответил 204) — страница показывает экран «Аккаунт удалён» */
  onDeleted: () => void;
}

/** «Мои данные» в конце профиля: скачать всё одним файлом и удалить аккаунт */
export default function ProfileData({ onDeleted }: ProfileDataProps) {
  const { t } = useI18n();
  const at = t.account;
  const showToast = useToast();
  const [exporting, setExporting] = useState(false);
  // В Telegram не узнать, сохранился ли файл, — после попытки подсказываем про бота
  const [showHint, setShowHint] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const download = async () => {
    if (exporting) return;
    haptic('light');
    setExporting(true);
    try {
      await downloadMyData();
      if (isInTelegram()) setShowHint(true);
      else showToast(at.export_done, 'success');
    } catch {
      showToast(at.export_error, 'error');
    } finally {
      setExporting(false);
    }
  };

  const remove = async () => {
    if (deleting) return;
    haptic('heavy');
    setDeleting(true);
    try {
      await deleteAccount();
      setConfirmOpen(false);
      onDeleted();
    } catch {
      setDeleting(false);
      showToast(at.delete_error, 'error');
    }
  };

  return (
    <>
      <ProfileSection title={at.title}>
        <li>
          <button
            type="button"
            className={ROW_CLASS}
            disabled={exporting}
            aria-busy={exporting}
            onClick={() => void download()}
          >
            {exporting ? (
              <span className="spinner size-5" aria-hidden="true" />
            ) : (
              <Icon name="download" className="size-5 text-[var(--primary)]" />
            )}
            <span className="min-w-0 flex-1">{exporting ? at.exporting : at.export}</span>
          </button>
          {showHint && (
            <p
              className="profile-data__hint m-0 flex flex-col items-start gap-2 px-4 pb-3 text-xs leading-relaxed text-[var(--text-secondary)]"
              role="status"
            >
              {at.export_hint}
              <SignLink
                url={botSectionUrl('profile')}
                className="text-sm font-semibold text-[var(--text-primary)] underline underline-offset-2"
              >
                {at.open_bot}
              </SignLink>
            </p>
          )}
        </li>
        <li>
          <button
            type="button"
            className={`${ROW_CLASS} text-[var(--danger)]`}
            onClick={() => {
              haptic('medium');
              setConfirmOpen(true);
            }}
          >
            <Icon name="trash" className="size-5" />
            <span className="min-w-0 flex-1">{at.delete}</span>
          </button>
        </li>
      </ProfileSection>

      <ConfirmDialog
        open={confirmOpen}
        title={at.delete_title}
        text={at.delete_text}
        confirmLabel={at.delete_confirm}
        danger
        busy={deleting}
        onConfirm={() => void remove()}
        onClose={() => {
          if (!deleting) setConfirmOpen(false);
        }}
      />
    </>
  );
}
