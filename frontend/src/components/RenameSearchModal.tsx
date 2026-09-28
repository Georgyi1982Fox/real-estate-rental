import { useId, useState } from 'react';
import type { FormEvent } from 'react';
import { useI18n } from '../providers/I18nProvider';
import { DIALOG_BUTTON_CLASS, DIALOG_CANCEL_CLASS } from './ConfirmDialog';
import Modal from './Modal';

const NAME_MAX_LENGTH = 100;

interface RenameSearchModalProps {
  open: boolean;
  /** Текущее название: подставляется в поле при открытии */
  initialName: string;
  busy?: boolean;
  onSubmit: (name: string) => void;
  onClose: () => void;
}

/** Модалка «Переименовать поиск»: одно поле, пустое название сохранить нельзя */
export default function RenameSearchModal({
  open,
  initialName,
  busy = false,
  onSubmit,
  onClose,
}: RenameSearchModalProps) {
  const { t } = useI18n();
  const st = t.searches;
  const inputId = useId();
  const [name, setName] = useState(initialName);
  const [openedWith, setOpenedWith] = useState<string | null>(null);

  // Каждое открытие начинается с текущего названия поиска
  const key = open ? initialName : null;
  if (openedWith !== key) {
    setOpenedWith(key);
    setName(initialName);
  }

  const trimmed = name.trim();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (trimmed && !busy) onSubmit(trimmed);
  };

  return (
    <Modal open={open} title={st.rename_title} onClose={onClose}>
      <form className="rename-search flex flex-col gap-2" onSubmit={handleSubmit}>
        <label htmlFor={inputId} className="text-sm font-medium">
          {st.name_label}
        </label>
        <input
          id={inputId}
          type="text"
          name="name"
          required
          maxLength={NAME_MAX_LENGTH}
          autoComplete="off"
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-3 text-base text-[var(--text-primary)]"
        />
        <footer className="rename-search__actions mt-4 flex gap-3">
          <button type="button" className={DIALOG_CANCEL_CLASS} onClick={onClose}>
            {t.common.cancel}
          </button>
          <button
            type="submit"
            className={`${DIALOG_BUTTON_CLASS} bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)]`}
            disabled={!trimmed || busy}
            aria-busy={busy}
          >
            {st.rename_save}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
