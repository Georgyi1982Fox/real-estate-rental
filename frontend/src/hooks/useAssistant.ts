import { useCallback, useSyncExternalStore } from 'react';
import { ApiError, apiPost } from '../api/client';
import type { AssistantAction, AssistantRequest, AssistantResponse, ListingId } from '../api/types';
import { showPremiumPrompt } from './usePremiumPrompt';

// AI-помощник в объявлении (FRONTEND-022). Ответ AI идёт 5–20 секунд и тратит дневной лимит,
// поэтому последний ответ по каждому объявлению хранится в localStorage: открыли объявление
// снова — текст, вопросы и галочки на месте. Сам лимит считает только бэкенд (ответ 429):
// здесь запрос никогда не блокируется заранее.
// Состояние общее на всё приложение: ушли со страницы, пока AI отвечает, — ответ всё равно
// сохранится, а кнопка по возвращении останется занятой.

const STORAGE_KEY = 'bina:assistant';
/** Столько объявлений помним; самое давнее вытесняется */
const MAX_LISTINGS = 20;

/** «Написать хозяину»: текст на грузинском, перевод и то, что человек написал о себе */
export interface OwnerMessage {
  text_ka: string;
  translation: string;
  note: string;
}

/** «Что спросить на просмотре»: вопросы и номера уже отмеченных */
export interface ViewingQuestions {
  items: string[];
  checked: number[];
}

interface SavedAnswers {
  /** ID объявления строкой: с бэкенда приходит UUID, из моков — число */
  id: string;
  message?: OwnerMessage;
  questions?: ViewingQuestions;
}

/** Чем закончился запрос: кнопке остаётся показать нужное сообщение */
export type AskResult = 'ok' | 'busy' | 'login' | 'premium' | 'limit' | 'failed';

/** Ошибка, о которой сообщаем рядом с кнопкой: лимит на день (429) или AI не ответил (502) */
export type AssistantProblem = Extract<AskResult, 'limit' | 'failed'>;

interface AssistantState {
  /** Сохранённые ответы, самые свежие — в начале */
  answers: SavedAnswers[];
  /** Объявления, по которым AI сейчас отвечает */
  pending: Record<string, AssistantAction>;
  /** «Осталось сегодня» из последнего ответа; null — ещё не спрашивали */
  remaining: number | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isStrings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

function readMessage(value: unknown): OwnerMessage | undefined {
  if (!isRecord(value)) return undefined;
  const { text_ka, translation, note } = value;
  if (typeof text_ka !== 'string' || !text_ka) return undefined;
  return {
    text_ka,
    translation: typeof translation === 'string' ? translation : '',
    note: typeof note === 'string' ? note : '',
  };
}

function readQuestions(value: unknown): ViewingQuestions | undefined {
  if (!isRecord(value) || !isStrings(value.items) || value.items.length === 0) return undefined;
  const checked = Array.isArray(value.checked)
    ? value.checked.filter((item): item is number => typeof item === 'number')
    : [];
  return { items: value.items, checked };
}

function load(): SavedAnswers[] {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? '[]');
    if (!Array.isArray(parsed)) return [];
    const answers: SavedAnswers[] = [];
    for (const item of parsed) {
      if (!isRecord(item) || typeof item.id !== 'string') continue;
      const message = readMessage(item.message);
      const questions = readQuestions(item.questions);
      if (message || questions) answers.push({ id: item.id, message, questions });
    }
    return answers.slice(0, MAX_LISTINGS);
  } catch {
    // localStorage недоступен (приватный режим) или запись испорчена — начинаем с пустого
    return [];
  }
}

let state: AssistantState = { answers: load(), pending: {}, remaining: null };
const listeners = new Set<() => void>();

function update(patch: Partial<AssistantState>): void {
  state = { ...state, ...patch };
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): AssistantState {
  return state;
}

/** Обновить ответы объявления; оно становится самым свежим в списке */
function saveAnswers(id: string, patch: Omit<SavedAnswers, 'id'>): void {
  const current = state.answers.find((item) => item.id === id);
  const answers = [
    { ...current, ...patch, id },
    ...state.answers.filter((item) => item.id !== id),
  ].slice(0, MAX_LISTINGS);
  update({ answers });
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(answers));
  } catch {
    // Не удалось сохранить — ответ останется до перезагрузки страницы
  }
}

function setPending(id: string, action: AssistantAction | null): void {
  const pending = { ...state.pending };
  if (action) pending[id] = action;
  else delete pending[id];
  update({ pending });
}

async function ask(id: string, action: AssistantAction, note: string): Promise<AskResult> {
  // Второй запрос, пока идёт первый, только зря потратит дневной лимит
  if (state.pending[id]) return 'busy';
  setPending(id, action);
  try {
    const body: AssistantRequest = { action, note };
    const data = await apiPost<AssistantResponse>(
      `/api/listings/${encodeURIComponent(id)}/assistant`,
      body,
    );
    if (typeof data.remaining_today === 'number') update({ remaining: data.remaining_today });

    if (action === 'message_owner') {
      if (!data.text_ka) return 'failed';
      saveAnswers(id, {
        message: { text_ka: data.text_ka, translation: data.translation ?? '', note },
      });
      return 'ok';
    }
    const items = (data.questions ?? []).filter(Boolean);
    if (items.length === 0) return 'failed';
    saveAnswers(id, { questions: { items, checked: [] } });
    return 'ok';
  } catch (error) {
    if (!(error instanceof ApiError)) return 'failed';
    if (error.isUnauthorized) return 'login';
    if (error.isPaymentRequired) {
      showPremiumPrompt('assistant');
      return 'premium';
    }
    if (error.status === 429) {
      update({ remaining: 0 });
      return 'limit';
    }
    // 502 — AI не ответил, 503 — AI не настроен, 0 — нет сети
    return 'failed';
  } finally {
    setPending(id, null);
  }
}

function toggleQuestion(id: string, index: number): void {
  const questions = state.answers.find((item) => item.id === id)?.questions;
  if (!questions) return;
  const checked = questions.checked.includes(index)
    ? questions.checked.filter((item) => item !== index)
    : [...questions.checked, index];
  saveAnswers(id, { questions: { ...questions, checked } });
}

export interface AssistantResult {
  message: OwnerMessage | undefined;
  questions: ViewingQuestions | undefined;
  /** Что AI сейчас составляет по этому объявлению (null — свободен) */
  busy: AssistantAction | null;
  remaining: number | null;
  ask: (action: AssistantAction, note?: string) => Promise<AskResult>;
  toggleQuestion: (index: number) => void;
}

/** AI-помощник объявления: сохранённые ответы и запрос нового (POST …/assistant) */
export function useAssistant(listingId: ListingId): AssistantResult {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot);
  const id = String(listingId);
  const saved = snapshot.answers.find((item) => item.id === id);

  return {
    message: saved?.message,
    questions: saved?.questions,
    busy: snapshot.pending[id] ?? null,
    remaining: snapshot.remaining,
    ask: useCallback((action, note = '') => ask(id, action, note.trim()), [id]),
    toggleQuestion: useCallback((index) => toggleQuestion(id, index), [id]),
  };
}
