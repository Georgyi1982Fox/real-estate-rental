// «Полная стоимость» квартиры (FRONTEND-025, бэкенд TASK-103): параметры расчёта и запрос

import type { ListingId } from '../api/types';

/** Границы параметров на сервере (иначе 422) */
export const PEOPLE_MIN = 1;
export const PEOPLE_MAX = 8;
export const MONTHS_MAX = 24;
/** Сколько месяцев въезда предлагаем: текущий и следующие */
const START_CHOICES = 12;

export const DEPOSIT_CHOICES = [0, 1, 2] as const;
export const FEE_CHOICES = [0, 50, 100] as const;

export interface CostSettings {
  people: number;
  months: number;
  /** Месяц въезда, «2026-11» */
  start: string;
  deposit: number;
  fee: number;
  utilitiesIncluded: boolean;
}

/** Число людей и срок обычно одни на все квартиры — их помним между объявлениями */
type Remembered = Pick<CostSettings, 'people' | 'months'>;

const STORAGE_KEY = 'bina:costs';

/** «2026-11» для месяца date */
function monthKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
}

/** Месяцы въезда на выбор: с текущего, на год вперёд */
export function startChoices(now: Date = new Date()): string[] {
  return Array.from({ length: START_CHOICES }, (_, offset) =>
    monthKey(new Date(now.getFullYear(), now.getMonth() + offset, 1)),
  );
}

function inRange(value: unknown, min: number, max: number): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= min && value <= max;
}

function loadRemembered(): Partial<Remembered> {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? '{}');
    if (typeof parsed !== 'object' || parsed === null) return {};
    const { people, months } = parsed as Record<string, unknown>;
    return {
      people: inRange(people, PEOPLE_MIN, PEOPLE_MAX) ? people : undefined,
      months: inRange(months, 1, MONTHS_MAX) ? months : undefined,
    };
  } catch {
    // localStorage недоступен или испорчен — берём значения по умолчанию
    return {};
  }
}

export function rememberCostSettings({ people, months }: CostSettings): void {
  try {
    const value: Remembered = { people, months };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // localStorage может быть недоступен (приватный режим)
  }
}

/** Значения по умолчанию — как на сервере: 2 человека, год, залог 1 месяц, без комиссии */
export function initialCostSettings(): CostSettings {
  const remembered = loadRemembered();
  return {
    people: remembered.people ?? 2,
    months: remembered.months ?? 12,
    start: startChoices()[0] ?? '',
    deposit: 1,
    fee: 0,
    utilitiesIncluded: false,
  };
}

/** GET /api/listings/{id}/costs с параметрами расчёта */
export function costsApiPath(listingId: ListingId, settings: CostSettings): string {
  const params = new URLSearchParams({
    people: String(settings.people),
    months: String(settings.months),
    start: settings.start,
    deposit_months: String(settings.deposit),
    agency_fee_percent: String(settings.fee),
    utilities_included: String(settings.utilitiesIncluded),
  });
  return `/api/listings/${encodeURIComponent(String(listingId))}/costs?${params.toString()}`;
}
