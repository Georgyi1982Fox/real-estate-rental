import type { FraudLevel, Listing } from '../api/types';
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
