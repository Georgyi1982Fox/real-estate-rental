import { useCallback, useState } from 'react';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import { haptic } from '../lib/telegram';

/** Локальный переключатель «Избранное» с toast и haptic (API избранного подключим отдельно) */
export function useFavorite(initial = false) {
  const [isFavorite, setIsFavorite] = useState(initial);
  const { t } = useI18n();
  const showToast = useToast();

  const toggle = useCallback(() => {
    const next = !isFavorite;
    setIsFavorite(next);
    showToast(next ? t.card.added : t.card.removed, 'success');
    haptic('light');
  }, [isFavorite, showToast, t]);

  return { isFavorite, toggle };
}
