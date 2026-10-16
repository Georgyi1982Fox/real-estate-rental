import type { SignedDocument, SignedDocumentStatus } from '../api/types';
import { useShareInvite } from '../hooks/useShareInvite';
import { fill, formatDate } from '../lib/format';
import { canSignNow } from '../lib/signing';
import type { DocumentPart } from '../lib/signing';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import type { IconName } from './Icon';
import SignLink from './SignLink';

const ACTION_CLASS =
  'inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-hover)] active:scale-[.98] disabled:opacity-60';
const SIGN_CLASS =
  'inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[var(--radius-md)] bg-[var(--primary)] px-3 py-2 text-sm font-semibold text-white shadow-[var(--shadow-sm)] hover:bg-[var(--primary-hover)] active:scale-[.98]';

const STATUS_CLASS: Record<SignedDocumentStatus, string> = {
  pending: 'bg-[var(--warning-bg)] text-[var(--warning-text)]',
  signed: 'bg-[var(--success-bg)] text-[var(--success-text)]',
  declined: 'bg-[var(--danger-bg)] text-[var(--danger-text)]',
};
const STATUS_ICON: Record<SignedDocumentStatus, IconName> = {
  pending: 'clock',
  signed: 'check',
  declined: 'ban',
};

interface DocumentCardProps {
  document: SignedDocument;
  /** Какой файл сейчас запрашивается у бота (на кнопке — индикатор) */
  busyPart: DocumentPart | null;
  /** Попросить бота прислать документ или сертификат в чат */
  onFile: (part: DocumentPart) => void;
}

/**
 * Документ в «Моих документах»: статус, кто и когда подписал, действия — подписать (создателю,
 * пока он не подписал), переслать ссылку, скачать, сертификат подписи (у подписанных)
 */
export default function DocumentCard({ document, busyPart, onFile }: DocumentCardProps) {
  const { lang, t } = useI18n();
  const st = t.signing;
  const shareInvite = useShareInvite();
  // Неизвестный статус от сервера показываем как «ждёт подписей»
  const status: SignedDocumentStatus =
    document.status in STATUS_CLASS ? document.status : 'pending';
  const inviteUrl = status === 'pending' ? document.invite_url : null;

  return (
    <article className="document-card flex min-w-0 flex-col gap-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[var(--shadow-sm)]">
      <header className="flex min-w-0 gap-3">
        <span className="document-card__icon grid size-11 shrink-0 place-items-center rounded-[var(--radius-md)] bg-[var(--surface-hover)] text-[var(--text-secondary)]">
          <Icon name={document.kind === 'acceptance' ? 'list_checks' : 'file'} className="size-6" />
        </span>
        <div className="min-w-0 flex-1 space-y-1">
          <p
            className={`document-card__status m-0 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold leading-5 ${STATUS_CLASS[status]}`}
          >
            <Icon name={STATUS_ICON[status]} className="size-3.5" />
            {st.statuses[status]}
          </p>
          <h2 className="m-0 break-words text-base font-semibold leading-6">{document.title}</h2>
          <p className="m-0 text-xs text-[var(--text-secondary)]">
            {fill(st.created, formatDate(document.created_at, lang))}
          </p>
        </div>
      </header>

      <section className="document-card__signers text-sm">
        {document.signers.length === 0 ? (
          <p className="m-0 text-[var(--text-secondary)]">{st.nobody_signed}</p>
        ) : (
          <>
            <h3 className="m-0 text-xs font-medium text-[var(--text-secondary)]">{st.signed_by}</h3>
            <ul className="m-0 mt-1 flex list-none flex-col gap-1 p-0">
              {document.signers.map((signer, index) => (
                <li key={`${signer.name}-${index}`} className="flex min-w-0 items-start gap-2">
                  <Icon name="check" className="mt-0.5 size-4 text-[var(--success-text)]" />
                  <span className="min-w-0 flex-1 break-words">
                    <span className="font-medium">{signer.name}</span>
                    {signer.me && <span className="text-[var(--text-secondary)]"> ({st.you})</span>}
                    <span className="text-[var(--text-secondary)]">
                      {' · '}
                      {formatDate(signer.signed_at, lang)}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <footer className="document-card__actions flex flex-wrap gap-2">
        {inviteUrl && canSignNow(document) && (
          <SignLink url={inviteUrl} className={SIGN_CLASS}>
            <Icon name="signature" className="size-4" />
            {st.sign}
          </SignLink>
        )}
        {inviteUrl && (
          <button
            type="button"
            className={ACTION_CLASS}
            onClick={() => void shareInvite(inviteUrl)}
          >
            <Icon name="forward" className="size-4" />
            {st.forward}
          </button>
        )}
        <button
          type="button"
          className={ACTION_CLASS}
          disabled={busyPart !== null}
          aria-busy={busyPart === 'document'}
          onClick={() => onFile('document')}
        >
          {busyPart === 'document' ? (
            <span className="spinner" aria-hidden="true" />
          ) : (
            <Icon name="download" className="size-4" />
          )}
          {st.download}
        </button>
        {status === 'signed' && (
          <button
            type="button"
            className={ACTION_CLASS}
            disabled={busyPart !== null}
            aria-busy={busyPart === 'certificate'}
            onClick={() => onFile('certificate')}
          >
            {busyPart === 'certificate' ? (
              <span className="spinner" aria-hidden="true" />
            ) : (
              <Icon name="badge_check" className="size-4" />
            )}
            {st.certificate}
          </button>
        )}
      </footer>
    </article>
  );
}
