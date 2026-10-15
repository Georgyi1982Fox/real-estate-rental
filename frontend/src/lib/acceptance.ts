// Акт приёмки квартиры (FRONTEND-024): черновик и его хранение, проверки, тело запроса

import { ApiError } from '../api/client';
import type {
  AcceptanceChecklist,
  AcceptanceItem,
  AcceptanceRequest,
  AcceptanceSection,
  ContractLanguage,
} from '../api/types';
import type { Lang } from '../i18n/strings';
import { today } from './contract';

export const ACCEPTANCE_PATH = '/acceptance';
/** Параметр адреса: акт для объявления (`/acceptance?listing=12`) */
export const ACCEPTANCE_LISTING_PARAM = 'listing';

/** Ограничения бэкенда (routes/acceptance.py) */
export const ACCEPTANCE_NAME_MIN = 2;
export const ACCEPTANCE_NAME_MAX = 120;
export const ACCEPTANCE_ADDRESS_MAX = 200;
export const ACCEPTANCE_COMMENT_MAX = 200;
export const ACCEPTANCE_METER_MAX = 20;
export const ACCEPTANCE_NOTES_MAX = 500;
export const ACCEPTANCE_KEYS_MAX = 50;

export const STATUS_OK = 'ok';
/** Только у этого состояния есть комментарий */
export const STATUS_DEFECT = 'defect';

const STORAGE_KEY = 'bina:acceptance';
/** Столько черновиков помним (акт без объявления + акты по объявлениям); старые вытесняются */
const DRAFTS_MAX = 5;
/** Ключ черновика акта без объявления */
const OWN_DRAFT = 'own';
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/** Отметка пункта: состояние и комментарий (комментарий уходит только с «Дефект») */
export interface AcceptanceMark {
  status: string;
  comment: string;
}

/** Черновик акта: числа — строками, как их набирает человек */
export interface AcceptanceDraft {
  /** Отмеченные пункты по коду; пункта без отметки здесь нет */
  items: Record<string, AcceptanceMark>;
  landlord_name: string;
  tenant_name: string;
  /** null — адрес из объявления, пока его не ввели сами */
  address: string | null;
  /** null — сегодня: черновик могли начать вчера */
  handover_date: string | null;
  keys: string;
  electricity: string;
  gas: string;
  water: string;
  notes: string;
  second_language: ContractLanguage;
}

/** Поля, у которых бывает ошибка; items — в чек-листе нет ни одной отметки */
export type AcceptanceField =
  | 'items'
  | 'landlord_name'
  | 'tenant_name'
  | 'address'
  | 'handover_date'
  | 'keys'
  | 'electricity'
  | 'gas'
  | 'water'
  | 'notes';

/** Что не так с полем: ключ текста в словаре (acceptance.errors, общие — contract.errors) */
export type AcceptanceProblem = 'items' | 'keys' | 'required' | 'name' | 'check';

export type AcceptanceErrors = Partial<Record<AcceptanceField, AcceptanceProblem>>;

/** Порядок на экране: к первому полю с ошибкой прокручиваем страницу */
export const ACCEPTANCE_FIELDS: AcceptanceField[] = [
  'items',
  'landlord_name',
  'tenant_name',
  'address',
  'handover_date',
  'keys',
  'electricity',
  'gas',
  'water',
  'notes',
];

/** Адрес страницы акта: для объявления или без него (из профиля) */
export function acceptancePath(listingId?: string | number): string {
  if (listingId === undefined) return ACCEPTANCE_PATH;
  return `${ACCEPTANCE_PATH}?${ACCEPTANCE_LISTING_PARAM}=${encodeURIComponent(String(listingId))}`;
}

/** Под каким ключом хранится черновик */
export function acceptanceDraftKey(listingId: string | null): string {
  return listingId ? `listing:${listingId}` : OWN_DRAFT;
}

/** Пустой акт; второй язык — язык интерфейса (для грузинского — английский, как на бэкенде) */
export function emptyAcceptanceDraft(lang: Lang): AcceptanceDraft {
  return {
    items: {},
    landlord_name: '',
    tenant_name: '',
    address: null,
    handover_date: null,
    keys: '',
    electricity: '',
    gas: '',
    water: '',
    notes: '',
    second_language: lang === 'ru' ? 'ru' : 'en',
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function text(value: unknown, max: number): string {
  return typeof value === 'string' ? value.slice(0, max) : '';
}

/** Черновик из localStorage: чужим данным не верим, берём только то, что похоже на акт */
function readDraft(value: unknown, lang: Lang): AcceptanceDraft | null {
  if (!isRecord(value)) return null;
  const draft = emptyAcceptanceDraft(lang);
  if (isRecord(value.items)) {
    for (const [code, mark] of Object.entries(value.items)) {
      if (!isRecord(mark) || typeof mark.status !== 'string') continue;
      draft.items[code] = {
        status: mark.status,
        comment: text(mark.comment, ACCEPTANCE_COMMENT_MAX),
      };
    }
  }
  draft.landlord_name = text(value.landlord_name, ACCEPTANCE_NAME_MAX);
  draft.tenant_name = text(value.tenant_name, ACCEPTANCE_NAME_MAX);
  if (typeof value.address === 'string')
    draft.address = text(value.address, ACCEPTANCE_ADDRESS_MAX);
  if (typeof value.handover_date === 'string' && DATE_RE.test(value.handover_date)) {
    draft.handover_date = value.handover_date;
  }
  draft.keys = text(value.keys, 2);
  draft.electricity = text(value.electricity, ACCEPTANCE_METER_MAX);
  draft.gas = text(value.gas, ACCEPTANCE_METER_MAX);
  draft.water = text(value.water, ACCEPTANCE_METER_MAX);
  draft.notes = text(value.notes, ACCEPTANCE_NOTES_MAX);
  if (value.second_language === 'ru' || value.second_language === 'en') {
    draft.second_language = value.second_language;
  }
  return draft;
}

interface StoredDraft {
  /** Когда меняли в последний раз: самый старый черновик вытесняется */
  saved: number;
  draft: unknown;
}

function readStore(): Record<string, StoredDraft> {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? '{}');
    if (!isRecord(parsed)) return {};
    const store: Record<string, StoredDraft> = {};
    for (const [key, entry] of Object.entries(parsed)) {
      if (isRecord(entry) && typeof entry.saved === 'number') {
        store[key] = { saved: entry.saved, draft: entry.draft };
      }
    }
    return store;
  } catch {
    // Хранилище недоступно или в нём не JSON — черновиков нет
    return {};
  }
}

function writeStore(store: Record<string, StoredDraft>): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch {
    // Хранилище недоступно или переполнено: акт останется только на экране
  }
}

export function loadAcceptanceDraft(key: string, lang: Lang): AcceptanceDraft | null {
  return readDraft(readStore()[key]?.draft, lang);
}

export function saveAcceptanceDraft(key: string, draft: AcceptanceDraft): void {
  const store = readStore();
  store[key] = { saved: Date.now(), draft };
  const fresh = Object.entries(store)
    .sort(([, a], [, b]) => b.saved - a.saved)
    .slice(0, DRAFTS_MAX);
  writeStore(Object.fromEntries(fresh));
}

export function removeAcceptanceDraft(key: string): void {
  const store = readStore();
  delete store[key];
  writeStore(store);
}

/** Дата, которую видит человек: своя или сегодняшняя */
export function acceptanceDate(draft: AcceptanceDraft): string {
  return draft.handover_date ?? today();
}

/** Адрес, который видит человек: свой или из объявления */
export function acceptanceAddress(draft: AcceptanceDraft, listingAddress: string): string {
  return draft.address ?? listingAddress.slice(0, ACCEPTANCE_ADDRESS_MAX);
}

/** Сколько пунктов раздела отмечено */
export function markedCount(section: AcceptanceSection, draft: AcceptanceDraft): number {
  return section.items.filter((item) => draft.items[item.code]).length;
}

/** Поставить или снять отметку: повторное нажатие на выбранное состояние снимает её */
export function toggleMark(
  draft: AcceptanceDraft,
  code: string,
  status: string,
): AcceptanceDraft['items'] {
  const items = { ...draft.items };
  const current = items[code];
  if (current?.status === status) delete items[code];
  // Комментарий помним: случайно сменили «Дефект» и вернулись — текст на месте
  else items[code] = { status, comment: current?.comment ?? '' };
  return items;
}

/** «Всё в порядке» для раздела: пункты без отметки — в порядке, уже отмеченные не трогаем */
export function markSectionOk(
  draft: AcceptanceDraft,
  section: AcceptanceSection,
): AcceptanceDraft['items'] {
  const items = { ...draft.items };
  for (const item of section.items) {
    if (!items[item.code]) items[item.code] = { status: STATUS_OK, comment: '' };
  }
  return items;
}

/** Отмеченные пункты в порядке чек-листа; отметки пунктов, которых в нём уже нет, пропускаем */
export function checkedItems(
  draft: AcceptanceDraft,
  checklist: AcceptanceChecklist,
): AcceptanceItem[] {
  const statuses = new Set(checklist.statuses.map((status) => status.code));
  return checklist.sections
    .flatMap((section) => section.items)
    .flatMap((item) => {
      const mark = draft.items[item.code];
      if (!mark || !statuses.has(mark.status)) return [];
      const comment = mark.status === STATUS_DEFECT ? mark.comment.trim() : '';
      return [{ code: item.code, status: mark.status, comment }];
    });
}

/** Те же проверки, что на сервере: что не так в акте (пусто — можно отправлять) */
export function acceptanceProblems(
  draft: AcceptanceDraft,
  checklist: AcceptanceChecklist,
  listingAddress: string,
): AcceptanceErrors {
  const errors: AcceptanceErrors = {};
  if (checkedItems(draft, checklist).length === 0) errors.items = 'items';
  if (draft.landlord_name.trim().length < ACCEPTANCE_NAME_MIN) errors.landlord_name = 'name';
  if (draft.tenant_name.trim().length < ACCEPTANCE_NAME_MIN) errors.tenant_name = 'name';
  if (!acceptanceAddress(draft, listingAddress).trim()) errors.address = 'required';
  if (!DATE_RE.test(acceptanceDate(draft))) errors.handover_date = 'required';
  // Пустое поле — «не указано»
  const keys = Number(draft.keys);
  if (
    draft.keys.trim() !== '' &&
    !(Number.isInteger(keys) && keys >= 0 && keys <= ACCEPTANCE_KEYS_MAX)
  ) {
    errors.keys = 'keys';
  }
  return errors;
}

/** Тело POST /api/documents/acceptance */
export function toAcceptanceRequest(
  draft: AcceptanceDraft,
  checklist: AcceptanceChecklist,
  listingAddress: string,
  listingId?: string,
): AcceptanceRequest {
  return {
    ...(listingId ? { listing_id: listingId } : {}),
    landlord_name: draft.landlord_name.trim(),
    tenant_name: draft.tenant_name.trim(),
    address: acceptanceAddress(draft, listingAddress).trim(),
    handover_date: acceptanceDate(draft),
    items: checkedItems(draft, checklist),
    keys: draft.keys.trim() === '' ? null : Number(draft.keys),
    electricity: draft.electricity.trim(),
    gas: draft.gas.trim(),
    water: draft.water.trim(),
    notes: draft.notes.trim(),
    second_language: draft.second_language,
    delivery: 'chat',
  };
}

function isAcceptanceField(name: string): name is AcceptanceField {
  return (ACCEPTANCE_FIELDS as string[]).includes(name);
}

/**
 * Ответ 422: какие поля сервер не принял. Список полей приходит в detail FastAPI
 * (ошибка внутри пункта — ["body", "items", 3, "comment"] — относится к чек-листу),
 * «address is required» — строкой (адреса нет ни в акте, ни в объявлении)
 */
export function acceptanceServerErrors(error: ApiError): AcceptanceErrors {
  const errors: AcceptanceErrors = {};
  for (const name of error.fields) {
    if (isAcceptanceField(name)) errors[name] = name === 'items' ? 'items' : 'check';
    else if (name === 'code' || name === 'status' || name === 'comment') errors.items = 'check';
  }
  if (error.detail?.includes('address')) errors.address = 'required';
  return errors;
}
