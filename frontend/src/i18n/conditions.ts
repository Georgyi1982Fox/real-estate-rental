// Названия состояний квартиры по кодам бэкенда (TASK-018): newly_renovated, white_frame, ...
// По образцу features.ts: неизвестный код не показывается.

import type { ConditionCode } from '../api/types';
import type { Lang } from './strings';

const CONDITIONS: Record<Lang, Record<string, string>> = {
  ka: {
    newly_renovated: 'ახალი გარემონტებული',
    renovated: 'გარემონტებული',
    needs_renovation: 'სარემონტო',
    under_renovation: 'მიმდინარე რემონტი',
    white_frame: 'თეთრი კარკასი',
    black_frame: 'შავი კარკასი',
    green_frame: 'მწვანე კარკასი',
  },
  ru: {
    newly_renovated: 'Новый ремонт',
    renovated: 'С ремонтом',
    needs_renovation: 'Требует ремонта',
    under_renovation: 'Идёт ремонт',
    white_frame: 'Белый каркас',
    black_frame: 'Чёрный каркас',
    green_frame: 'Зелёный каркас',
  },
  en: {
    newly_renovated: 'Newly renovated',
    renovated: 'Renovated',
    needs_renovation: 'Needs renovation',
    under_renovation: 'Under renovation',
    white_frame: 'White frame',
    black_frame: 'Black frame',
    green_frame: 'Green frame',
  },
};

/** Состояния для фильтра */
export const CONDITION_CODES = [
  'newly_renovated',
  'renovated',
  'needs_renovation',
  'under_renovation',
  'white_frame',
  'black_frame',
  'green_frame',
] as const satisfies readonly ConditionCode[];

/** Название состояния на языке интерфейса; undefined — кода нет или он неизвестен */
export function conditionName(code: string | null | undefined, lang: Lang): string | undefined {
  if (!code) return undefined;
  return (CONDITIONS[lang] ?? CONDITIONS.ru)[code];
}
