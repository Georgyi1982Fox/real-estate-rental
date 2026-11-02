import { useCallback, useRef, useState } from 'react';
import type { ChangeEvent } from 'react';
import { Link } from 'react-router-dom';
import { apiUpload } from '../api/client';
import type { AgencyCabinet } from '../api/types';
import {
  AGENCY_API,
  AGENCY_LOGO_MAX_BYTES,
  agencyErrorText,
  agencyPagePath,
  agencyShare,
} from '../lib/agency';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import AgencyEditModal from './AgencyEditModal';
import AgencyLogo from './AgencyLogo';
import Icon from './Icon';
import { MY_CARD_ACTION_CLASS } from './MyHotelCard';
import ShareButton from './ShareButton';

const LOGO_TYPES = 'image/jpeg,image/png,image/webp';

interface AgencyHeaderProps {
  agency: AgencyCabinet;
  /** Сервер после каждой правки отдаёт кабинет целиком */
  onChange: (agency: AgencyCabinet) => void;
}

/** Шапка кабинета: логотип (нажатие — загрузить новый), название, описание и правка */
export default function AgencyHeader({ agency, onChange }: AgencyHeaderProps) {
  const { t } = useI18n();
  const at = t.agency;
  const showToast = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [editing, setEditing] = useState(false);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeEdit = useCallback(() => setEditing(false), []);

  const fail = (text: string) => {
    haptic('error');
    showToast(text, 'error');
  };

  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    // Тот же файл можно выбрать снова
    event.target.value = '';
    if (!file) return;
    if (file.size > AGENCY_LOGO_MAX_BYTES) {
      fail(at.errors.photo_size);
      return;
    }
    setUploading(true);
    try {
      onChange(await apiUpload<AgencyCabinet>(`${AGENCY_API}/logo`, file));
      haptic('success');
    } catch (error) {
      fail(agencyErrorText(error, at));
    } finally {
      setUploading(false);
    }
  };

  return (
    <header className="agency-header flex flex-col gap-4 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[var(--shadow-sm)] sm:p-5">
      <div className="flex min-w-0 items-start gap-4">
        <input
          ref={inputRef}
          type="file"
          accept={LOGO_TYPES}
          className="sr-only"
          tabIndex={-1}
          aria-hidden="true"
          onChange={(event) => void upload(event)}
        />
        <button
          type="button"
          className="agency-header__logo relative shrink-0 rounded-2xl active:scale-[.98] disabled:opacity-70"
          aria-label={at.logo}
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          <AgencyLogo
            url={agency.logo_url}
            className="size-20 rounded-2xl"
            iconClassName="size-9 stroke-[1.5]"
          />
          <span className="absolute -right-1 -bottom-1 grid size-7 place-items-center rounded-full border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] shadow-[var(--shadow-sm)]">
            {uploading ? (
              <span className="spinner" aria-hidden="true" />
            ) : (
              <Icon name="image" className="size-3.5" />
            )}
          </span>
        </button>
        <div className="min-w-0 flex-1 space-y-1">
          <h1
            id="agency-title"
            className="break-words text-xl font-bold leading-tight tracking-tight sm:text-2xl"
          >
            {agency.name}
          </h1>
          {agency.description ? (
            <p className="m-0 whitespace-pre-line break-words text-sm leading-snug text-[var(--text-secondary)]">
              {agency.description}
            </p>
          ) : (
            <p className="m-0 text-sm text-[var(--text-secondary)]">{at.no_description}</p>
          )}
        </div>
      </div>

      <footer className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className={MY_CARD_ACTION_CLASS}
          aria-haspopup="dialog"
          onClick={() => {
            haptic('light');
            setEditing(true);
          }}
        >
          <Icon name="pencil" className="size-4" />
          {at.edit}
        </button>
        <Link
          to={agencyPagePath(agency.id)}
          className={MY_CARD_ACTION_CLASS}
          onClick={() => haptic('light')}
        >
          <Icon name="eye" className="size-4" />
          {at.public_page}
        </Link>
        <ShareButton share={agencyShare(agency.id, agency.name)} label={at.share} />
      </footer>

      <AgencyEditModal agency={agency} open={editing} onSaved={onChange} onClose={closeEdit} />
    </header>
  );
}
