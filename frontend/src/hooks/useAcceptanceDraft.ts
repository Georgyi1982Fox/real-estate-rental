import { useCallback, useEffect, useRef, useState } from 'react';
import {
  emptyAcceptanceDraft,
  loadAcceptanceDraft,
  removeAcceptanceDraft,
  saveAcceptanceDraft,
} from '../lib/acceptance';
import type { AcceptanceDraft } from '../lib/acceptance';
import { useI18n } from '../providers/I18nProvider';

interface DraftState {
  key: string;
  draft: AcceptanceDraft;
}

/**
 * Черновик акта приёмки: живёт в localStorage, чтобы не потерять отметки, если мини-апп
 * закрыли посреди обхода квартиры. key — свой для каждого объявления и для акта без него
 */
export function useAcceptanceDraft(key: string) {
  const { lang } = useI18n();
  const open = (): DraftState => ({
    key,
    draft: loadAcceptanceDraft(key, lang) ?? emptyAcceptanceDraft(lang),
  });
  const [state, setState] = useState<DraftState>(open);
  // Нетронутый пустой акт в хранилище не пишем
  const dirty = useRef(false);

  // Открыли акт другого объявления — берём его черновик
  if (state.key !== key) setState(open());

  useEffect(() => {
    if (!dirty.current) return;
    dirty.current = false;
    saveAcceptanceDraft(state.key, state.draft);
  }, [state]);

  const change = useCallback((patch: Partial<AcceptanceDraft>) => {
    dirty.current = true;
    setState((current) => ({ ...current, draft: { ...current.draft, ...patch } }));
  }, []);

  /** Начать акт заново: черновик удаляется */
  const reset = useCallback(() => {
    dirty.current = false;
    removeAcceptanceDraft(key);
    setState({ key, draft: emptyAcceptanceDraft(lang) });
  }, [key, lang]);

  return { draft: state.draft, change, reset };
}
