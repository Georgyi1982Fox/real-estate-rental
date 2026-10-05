import { useCallback, useState } from 'react';
import type { SearchFilters } from '../api/types';
import { useSavedSearches } from '../hooks/useSavedSearches';
import { hasFilters } from '../lib/searchFilters';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import Icon from './Icon';
import Modal from './Modal';
import OpenInTelegram from './OpenInTelegram';

interface SaveSearchButtonProps {
  /** Всё, что выбрано: фильтры и текст поиска (q) */
  filters: SearchFilters;
}

/**
 * «Сохранить поиск»: активна, когда выбран хоть один фильтр или введён текст поиска
 * и такого поиска ещё нет.
 * Без Telegram (гость, 401) открывает модалку «Откройте в Telegram».
 */
export default function SaveSearchButton({ filters }: SaveSearchButtonProps) {
  const { t } = useI18n();
  const st = t.searches;
  const showToast = useToast();
  const { loading, unauthorized, save, findByFilters } = useSavedSearches();
  const [saving, setSaving] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeLogin = useCallback(() => setLoginOpen(false), []);

  const saved = !unauthorized && findByFilters(filters) !== undefined;
  const disabled = !hasFilters(filters) || saved || saving || (loading && !unauthorized);

  const handleClick = async () => {
    haptic('light');
    if (unauthorized) {
      setLoginOpen(true);
      return;
    }
    setSaving(true);
    const created = await save(filters);
    setSaving(false);
    if (created) {
      showToast(st.saved_toast, 'success');
      haptic('success');
    }
  };

  return (
    <>
      <button
        type="button"
        className="save-search inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-md)] border border-[var(--primary)] bg-[var(--surface)] px-4 py-2.5 text-sm font-semibold text-[var(--primary)] shadow-[var(--shadow-sm)] hover:bg-[var(--surface-hover)] active:scale-[.98] disabled:border-[var(--border)] disabled:text-[var(--text-secondary)] disabled:shadow-none disabled:hover:bg-[var(--surface)]"
        disabled={disabled}
        aria-busy={saving}
        onClick={() => void handleClick()}
      >
        {saved ? (
          <Icon name="check" className="size-5" />
        ) : (
          <Icon name="bell" className={`size-5 ${disabled ? '' : 'bell-ring'}`} />
        )}
        <span>{saved ? st.saved : saving ? st.saving : st.save}</span>
      </button>

      <Modal open={loginOpen} title={st.save} onClose={closeLogin}>
        <OpenInTelegram plain />
      </Modal>
    </>
  );
}
