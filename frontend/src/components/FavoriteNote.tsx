import { useRef, useState } from 'react';
import type { ListingId } from '../api/types';
import { NOTE_MAX_LENGTH, useFavoriteNotes } from '../hooks/useFavoriteNotes';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import { DIALOG_CANCEL_CLASS } from './ConfirmDialog';
import Icon from './Icon';
import TextAreaField from './TextAreaField';

const BUTTON_CLASS =
  'inline-flex min-h-11 flex-1 items-center justify-center rounded-[var(--radius-md)] px-4 py-2.5 text-sm font-semibold active:scale-[.98] disabled:opacity-60';
const LINK_CLASS =
  'inline-flex min-h-11 items-center gap-1.5 rounded-[var(--radius-sm)] text-sm font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)]';

interface FavoriteNoteProps {
  listingId: ListingId;
  className?: string;
}

/**
 * «📝 Заметка» к квартире в избранном (FRONTEND-043): видна только самому человеку.
 * Показывать — только когда квартира в избранном; гостю в браузере поля нет
 */
export default function FavoriteNote({ listingId, className = '' }: FavoriteNoteProps) {
  const { t } = useI18n();
  const ft = t.favorites;
  const showToast = useToast();
  const { enabled, noteOf, save } = useFavoriteNotes();
  const note = noteOf(listingId);
  const [draft, setDraft] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  // Двойное нажатие приходит раньше, чем обновится состояние
  const pending = useRef(false);

  if (!enabled) return null;

  const startEditing = () => {
    haptic('light');
    setDraft(note);
  };

  const submit = async () => {
    if (draft === null || pending.current) return;
    const text = draft.trim();
    if (text === note) {
      setDraft(null);
      return;
    }
    pending.current = true;
    setSaving(true);
    const result = await save(listingId, text);
    pending.current = false;
    setSaving(false);
    if (result === 'saved') {
      haptic('success');
      showToast(text ? ft.note_saved : ft.note_deleted, 'success');
      setDraft(null);
    } else {
      haptic('error');
      showToast(result === 'gone' ? ft.note_gone : ft.note_error, 'error');
    }
  };

  if (draft !== null) {
    return (
      <form
        className={`favorite-note flex flex-col gap-3 ${className}`}
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <TextAreaField
          label={ft.note_label}
          value={draft}
          maxLength={NOTE_MAX_LENGTH}
          hint={ft.note_hint}
          placeholder={ft.note_placeholder}
          // Поле открылось по нажатию «Добавить» / «Изменить» — сразу печатаем
          autoFocus
          onChange={(event) => setDraft(event.target.value)}
        />
        <div className="favorite-note__actions flex gap-3">
          <button type="button" className={DIALOG_CANCEL_CLASS} onClick={() => setDraft(null)}>
            {t.common.cancel}
          </button>
          <button
            type="submit"
            className={`${BUTTON_CLASS} bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)]`}
            disabled={saving}
            aria-busy={saving}
          >
            {ft.note_save}
          </button>
        </div>
      </form>
    );
  }

  if (!note) {
    return (
      <div className={`favorite-note ${className}`}>
        <button type="button" className={LINK_CLASS} onClick={startEditing}>
          <span aria-hidden="true">📝</span>
          {ft.note_add}
        </button>
      </div>
    );
  }

  return (
    <section
      className={`favorite-note rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-hover)] p-3 ${className}`}
      aria-label={ft.note_label}
    >
      <header className="flex items-center justify-between gap-3">
        <p className="m-0 text-xs font-semibold text-[var(--text-secondary)]">{ft.note_label}</p>
        <button
          type="button"
          className="favorite-note__edit inline-flex min-h-9 items-center gap-1 rounded-[var(--radius-sm)] px-1 text-xs font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)]"
          onClick={startEditing}
        >
          <Icon name="pencil" className="size-3.5" />
          {ft.note_edit}
        </button>
      </header>
      <p className="favorite-note__text m-0 mt-1 whitespace-pre-line break-words text-sm leading-relaxed">
        {note}
      </p>
    </section>
  );
}
