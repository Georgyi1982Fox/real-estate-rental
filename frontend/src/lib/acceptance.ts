// Акт приёмки квартиры (FRONTEND-024): черновик и его хранение, проверки, тело запроса

import { ApiError } from '../api/client';
import type {
  AcceptanceChecklist,
  AcceptanceItem,
  AcceptanceRequest,
  AcceptanceRoomType,
  ContractLanguage,
  DocumentDelivery,
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

/** Добавленная комната: тип и номер среди комнат этого типа (Спальня 1, Спальня 2) */
export interface AcceptanceRoom {
  type: string;
  n: number;
}

/** Черновик акта: числа — строками, как их набирает человек */
export interface AcceptanceDraft {
  /** Комнаты в порядке добавления; сначала их нет — человек добавляет те, что есть в квартире */
  rooms: AcceptanceRoom[];
  /** Отмеченные пункты по коду (`bedroom-2:windows`); пункта без отметки здесь нет */
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
    rooms: [],
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
  if (Array.isArray(value.rooms)) {
    const seen = new Set<string>();
    for (const room of value.rooms) {
      if (!isRecord(room) || typeof room.type !== 'string' || typeof room.n !== 'number') continue;
      if (!Number.isInteger(room.n) || room.n < 1 || room.n > ROOM_NUMBER_MAX) continue;
      const key = roomKey({ type: room.type, n: room.n });
      if (seen.has(key)) continue;
      seen.add(key);
      draft.rooms.push({ type: room.type, n: room.n });
    }
  }
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

/** Номер комнаты в черновике не больше этого (у бэкенда предел — max_count типа) */
const ROOM_NUMBER_MAX = 20;

/** Ключ комнаты: `bedroom-2` */
export function roomKey(room: AcceptanceRoom): string {
  return `${room.type}-${room.n}`;
}

/** Код пункта комнаты для бэкенда: `bedroom-2:windows` */
export function roomItemCode(room: AcceptanceRoom, itemCode: string): string {
  return `${roomKey(room)}:${itemCode}`;
}

/** Комнаты, которые знает чек-лист, — по порядку типов, внутри типа — по номеру */
export function orderedRooms(
  draft: AcceptanceDraft,
  checklist: AcceptanceChecklist,
): { room: AcceptanceRoom; type: AcceptanceRoomType }[] {
  const order = new Map(checklist.rooms.map((type, index) => [type.code, index]));
  return draft.rooms
    .flatMap((room) => {
      const type = checklist.rooms.find((candidate) => candidate.code === room.type);
      return type && room.n <= type.max_count ? [{ room, type }] : [];
    })
    .sort(
      (a, b) =>
        (order.get(a.room.type) ?? 0) - (order.get(b.room.type) ?? 0) || a.room.n - b.room.n,
    );
}

/** Сколько комнат этого типа уже добавлено */
export function roomCount(draft: AcceptanceDraft, type: string): number {
  return draft.rooms.filter((room) => room.type === type).length;
}

/**
 * Добавить комнату: номер — самый маленький свободный (удалили «Спальню 2» — следующая
 * снова 2). null — комнат этого типа уже предельное число
 */
export function addRoom(draft: AcceptanceDraft, type: AcceptanceRoomType): AcceptanceRoom | null {
  const taken = new Set(draft.rooms.filter((room) => room.type === type.code).map((room) => room.n));
  for (let n = 1; n <= type.max_count; n += 1) {
    if (!taken.has(n)) return { type: type.code, n };
  }
  return null;
}

/** Убрать комнату вместе с её отметками */
export function removeRoom(
  draft: AcceptanceDraft,
  room: AcceptanceRoom,
): Pick<AcceptanceDraft, 'rooms' | 'items'> {
  const key = roomKey(room);
  const prefix = `${key}:`;
  return {
    rooms: draft.rooms.filter((candidate) => roomKey(candidate) !== key),
    items: Object.fromEntries(
      Object.entries(draft.items).filter(([code]) => !code.startsWith(prefix)),
    ),
  };
}

/** Название комнаты: номер — только если таких комнат несколько (или это не первая) */
export function roomTitle(
  room: AcceptanceRoom,
  type: AcceptanceRoomType,
  draft: AcceptanceDraft,
): string {
  return room.n > 1 || roomCount(draft, room.type) > 1 ? `${type.title} ${room.n}` : type.title;
}

/** Сколько пунктов комнаты отмечено */
export function roomMarked(
  draft: AcceptanceDraft,
  room: AcceptanceRoom,
  type: AcceptanceRoomType,
): number {
  return type.items.filter((item) => draft.items[roomItemCode(room, item.code)]).length;
}

/** Сколько пунктов во всех добавленных комнатах */
export function roomsTotal(draft: AcceptanceDraft, checklist: AcceptanceChecklist): number {
  return orderedRooms(draft, checklist).reduce((count, { type }) => count + type.items.length, 0);
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

/** «Всё в порядке» для комнаты: пункты без отметки — в порядке, уже отмеченные не трогаем */
export function markRoomOk(
  draft: AcceptanceDraft,
  room: AcceptanceRoom,
  type: AcceptanceRoomType,
): AcceptanceDraft['items'] {
  const items = { ...draft.items };
  for (const item of type.items) {
    const code = roomItemCode(room, item.code);
    if (!items[code]) items[code] = { status: STATUS_OK, comment: '' };
  }
  return items;
}

/**
 * Отмеченные пункты добавленных комнат, по порядку комнат. Отметки комнат и пунктов,
 * которых уже нет (и старого чек-листа разделами), в акт не идут
 */
export function checkedItems(
  draft: AcceptanceDraft,
  checklist: AcceptanceChecklist,
): AcceptanceItem[] {
  const statuses = new Set(checklist.statuses.map((status) => status.code));
  return orderedRooms(draft, checklist).flatMap(({ room, type }) =>
    type.items.flatMap((item) => {
      const code = roomItemCode(room, item.code);
      const mark = draft.items[code];
      if (!mark || !statuses.has(mark.status)) return [];
      const comment = mark.status === STATUS_DEFECT ? mark.comment.trim() : '';
      return [{ code, status: mark.status, comment }];
    }),
  );
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

/** Тело POST /api/documents/acceptance: в чат или на подпись */
export function toAcceptanceRequest(
  draft: AcceptanceDraft,
  checklist: AcceptanceChecklist,
  listingAddress: string,
  listingId?: string,
  delivery: DocumentDelivery = 'chat',
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
    delivery,
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
