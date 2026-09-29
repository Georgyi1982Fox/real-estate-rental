import { useSyncExternalStore } from 'react';

// Окно «Подключить Premium» при ошибке 402. Избранное и сохранение поиска вызываются из
// многих мест (карточки, страница квартиры, фильтры), поэтому окно одно на всё приложение —
// PremiumLimitModal в Layout, а хуки только сообщают причину через showPremiumPrompt()

/** Какой лимит бесплатного тарифа исчерпан */
export type PremiumLimitReason = 'favorites' | 'searches';

let reason: PremiumLimitReason | null = null;
const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): PremiumLimitReason | null {
  return reason;
}

export function showPremiumPrompt(next: PremiumLimitReason): void {
  reason = next;
  emit();
}

export function hidePremiumPrompt(): void {
  if (reason === null) return;
  reason = null;
  emit();
}

/** Текущая причина показа окна (null — окно закрыто) */
export function usePremiumPrompt(): PremiumLimitReason | null {
  return useSyncExternalStore(subscribe, getSnapshot);
}
