import type { FraudLevel, Listing, RiskReason } from '../api/types';
import type { Strings } from '../i18n/strings';

type FraudReasons = Strings['listing']['fraud']['reasons'];

/** Уровень риска; отсутствующее или незнакомое значение считаем 'none' */
export function fraudLevel(listing: Pick<Listing, 'fraud_level'>): FraudLevel {
  const level = listing.fraud_level;
  return level === 'warning' || level === 'high' ? level : 'none';
}

/** Тексты причин на языке интерфейса. Неизвестные коды пропускаем — бэкенд может добавлять новые */
export function fraudReasonTexts(codes: string[] | undefined, reasons: FraudReasons): string[] {
  const known = (code: string): code is keyof FraudReasons => Object.hasOwn(reasons, code);
  return [...new Set(codes ?? [])].filter(known).map((code) => reasons[code]);
}

export interface RiskReasonItem {
  key: string;
  title: string;
  /** Только с Premium */
  explanation: string;
}

/**
 * Причины для блока «Почему?»: название с бэкенда (Premium), иначе свой текст по коду.
 * Причина без названия и с незнакомым кодом пропускается. Бэкенд причин не прислал —
 * берём коды из самого объявления.
 */
export function riskReasonItems(
  riskReasons: RiskReason[] | undefined,
  codes: string[] | undefined,
  reasons: FraudReasons,
): RiskReasonItem[] {
  const source: RiskReason[] =
    riskReasons && riskReasons.length > 0
      ? riskReasons
      : (codes ?? []).map((code) => ({ code, title: null, explanation: null }));
  const seen = new Set<string>();
  const items: RiskReasonItem[] = [];
  for (const reason of source) {
    const title = reason.title?.trim() || fraudReasonTexts([reason.code], reasons)[0] || '';
    if (!title || seen.has(title)) continue;
    seen.add(title);
    items.push({ key: title, title, explanation: reason.explanation?.trim() ?? '' });
  }
  return items;
}
