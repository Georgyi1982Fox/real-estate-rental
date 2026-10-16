// Подпись документов (FRONTEND-042, бэкенд — TASK-115): договор и акт приёмки отправляют
// на подпись, подписывают в чате с ботом, список — «Мои документы» в профиле

import type { FormEvent } from 'react';
import type { DocumentDelivery, SignedDocument } from '../api/types';

export const DOCUMENTS_PATH = '/documents';

/** Что прислать ещё раз: сам документ или сертификат подписи (только у подписанных) */
export type DocumentPart = 'document' | 'certificate';

/** Ссылка «Поделиться» в Telegram: человек выбирает чат, куда переслать ссылку на подпись */
export function shareInviteUrl(inviteUrl: string): string {
  return `https://t.me/share/url?url=${encodeURIComponent(inviteUrl)}`;
}

/** GET …/file: бот присылает документ или сертификат в чат */
export function documentFilePath(id: string, part: DocumentPart): string {
  const params = new URLSearchParams({ part, delivery: 'chat' });
  return `/api/documents/${encodeURIComponent(id)}/file?${params.toString()}`;
}

/** Создатель ещё не подписал свой документ: ссылка есть только у создателя, пока ждёт подписей */
export function canSignNow(document: SignedDocument): boolean {
  return (
    document.status === 'pending' &&
    Boolean(document.invite_url) &&
    !document.signers.some((signer) => signer.me)
  );
}

/** Какой кнопкой отправлена форма: «Получить договор / акт» (в чат) или «Отправить на подпись» */
export function submitDelivery(event: FormEvent<HTMLFormElement>): DocumentDelivery {
  const { submitter } = event.nativeEvent as SubmitEvent;
  return submitter instanceof HTMLElement && submitter.dataset.delivery === 'sign'
    ? 'sign'
    : 'chat';
}
