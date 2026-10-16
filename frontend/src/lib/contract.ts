// Анкета договора аренды (FRONTEND-023): черновик, проверки, тело запроса, ошибки сервера

import { ApiError } from '../api/client';
import type {
  ContractLanguage,
  ContractRequest,
  ContractUtilities,
  Currency,
  DocumentDelivery,
  Listing,
} from '../api/types';
import type { Lang } from '../i18n/strings';
import { tr } from './format';

/** Ограничения бэкенда (routes/contract.py) */
export const CONTRACT_NAME_MIN = 2;
export const CONTRACT_NAME_MAX = 120;
export const CONTRACT_ID_MAX = 40;
export const CONTRACT_ADDRESS_MAX = 200;
export const CONTRACT_NOTES_MAX = 500;
export const CONTRACT_MONTHS_MAX = 60;
export const CONTRACT_PAYMENT_DAY_MAX = 28;
export const CONTRACT_MONEY_MAX = 1_000_000;

/** Сроки-кнопки; любое другое число месяцев вводится рядом */
export const CONTRACT_MONTHS_PRESETS: number[] = [3, 6, 12];
export const CONTRACT_CURRENCIES: Currency[] = ['GEL', 'USD', 'EUR'];
export const CONTRACT_UTILITIES: ContractUtilities[] = ['tenant', 'landlord', 'included'];
export const CONTRACT_LANGUAGES: ContractLanguage[] = ['ru', 'en'];

const DEFAULT_MONTHS = 12;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/** Черновик анкеты: числа — строками, как их набирает человек */
export interface ContractDraft {
  landlord_name: string;
  landlord_id: string;
  tenant_name: string;
  tenant_id: string;
  address: string;
  start_date: string;
  months: string;
  rent: string;
  currency: Currency;
  /** null — депозит равен плате и меняется вместе с ней, пока его не ввели сами */
  deposit: string | null;
  payment_day: string;
  utilities: ContractUtilities;
  pets_allowed: boolean;
  notes: string;
  second_language: ContractLanguage;
}

/** Поля, у которых бывает ошибка */
export type ContractField =
  | 'landlord_name'
  | 'landlord_id'
  | 'tenant_name'
  | 'tenant_id'
  | 'address'
  | 'start_date'
  | 'months'
  | 'rent'
  | 'deposit'
  | 'payment_day'
  | 'notes';

/** Что не так с полем: ключ текста в словаре (contract.errors) */
export type ContractProblem = 'required' | 'name' | 'months' | 'amount' | 'payment_day' | 'check';

export type ContractErrors = Partial<Record<ContractField, ContractProblem>>;

/** Порядок полей на экране: к первому с ошибкой прокручиваем форму */
export const CONTRACT_FIELDS: ContractField[] = [
  'landlord_name',
  'landlord_id',
  'tenant_name',
  'tenant_id',
  'address',
  'start_date',
  'months',
  'rent',
  'deposit',
  'payment_day',
  'notes',
];

/** Сегодня по местному времени: 2026-11-01 */
export function today(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

function isCurrency(value: string): value is Currency {
  return (CONTRACT_CURRENCIES as string[]).includes(value);
}

/**
 * Пустая анкета: адрес, плата и валюта — из объявления, второй язык — язык интерфейса
 * (для грузинского — английский, как на бэкенде)
 */
export function contractDraft(listing: Listing, lang: Lang): ContractDraft {
  // Цена посуточного объявления — за сутки: месячную плату человек вводит сам
  const monthly = listing.rent_period !== 'daily';
  return {
    landlord_name: '',
    landlord_id: '',
    tenant_name: '',
    tenant_id: '',
    address: tr(listing.address, lang).trim().slice(0, CONTRACT_ADDRESS_MAX),
    start_date: today(),
    months: String(DEFAULT_MONTHS),
    rent: monthly && listing.price > 0 ? String(listing.price) : '',
    currency: isCurrency(listing.currency) ? listing.currency : 'GEL',
    deposit: null,
    payment_day: '1',
    utilities: 'tenant',
    pets_allowed: false,
    notes: '',
    second_language: lang === 'ru' ? 'ru' : 'en',
  };
}

/** Депозит, который видит человек: свой или равный плате */
export function contractDeposit(draft: ContractDraft): string {
  return draft.deposit ?? draft.rent;
}

function isWhole(text: string, min: number, max: number): boolean {
  const value = Number(text);
  return text.trim() !== '' && Number.isInteger(value) && value >= min && value <= max;
}

function isMoney(text: string, allowZero: boolean): boolean {
  const value = Number(text);
  if (text.trim() === '' || !Number.isFinite(value) || value > CONTRACT_MONEY_MAX) return false;
  return allowZero ? value >= 0 : value > 0;
}

/** Те же проверки, что на сервере: что не так в анкете (пусто — можно отправлять) */
export function contractProblems(draft: ContractDraft): ContractErrors {
  const errors: ContractErrors = {};
  if (draft.landlord_name.trim().length < CONTRACT_NAME_MIN) errors.landlord_name = 'name';
  if (draft.tenant_name.trim().length < CONTRACT_NAME_MIN) errors.tenant_name = 'name';
  if (!draft.address.trim()) errors.address = 'required';
  if (!DATE_RE.test(draft.start_date)) errors.start_date = 'required';
  if (!isWhole(draft.months, 1, CONTRACT_MONTHS_MAX)) errors.months = 'months';
  if (!isMoney(draft.rent, false)) errors.rent = 'amount';
  // Пустой депозит — «без депозита»
  const deposit = contractDeposit(draft);
  if (deposit.trim() !== '' && !isMoney(deposit, true)) errors.deposit = 'amount';
  if (!isWhole(draft.payment_day, 1, CONTRACT_PAYMENT_DAY_MAX)) errors.payment_day = 'payment_day';
  return errors;
}

/** Тело POST /api/listings/{id}/contract: в чат или на подпись */
export function toContractRequest(
  draft: ContractDraft,
  delivery: DocumentDelivery = 'chat',
): ContractRequest {
  return {
    landlord_name: draft.landlord_name.trim(),
    tenant_name: draft.tenant_name.trim(),
    landlord_id: draft.landlord_id.trim(),
    tenant_id: draft.tenant_id.trim(),
    address: draft.address.trim(),
    start_date: draft.start_date,
    months: Number(draft.months),
    rent: Number(draft.rent),
    currency: draft.currency,
    deposit: Number(contractDeposit(draft)) || 0,
    payment_day: Number(draft.payment_day),
    utilities: draft.utilities,
    pets_allowed: draft.pets_allowed,
    notes: draft.notes.trim(),
    second_language: draft.second_language,
    delivery,
  };
}

function isContractField(name: string): name is ContractField {
  return (CONTRACT_FIELDS as string[]).includes(name);
}

/**
 * Ответ 422: какие поля сервер не принял. Список полей приходит в detail FastAPI,
 * «address is required» — строкой (адреса нет ни в анкете, ни в объявлении)
 */
export function contractServerErrors(error: ApiError): ContractErrors {
  const errors: ContractErrors = {};
  for (const name of error.fields) {
    if (isContractField(name)) errors[name] = 'check';
  }
  if (error.detail?.includes('address')) errors.address = 'required';
  return errors;
}
