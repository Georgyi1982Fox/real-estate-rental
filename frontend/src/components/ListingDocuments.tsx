import { useCallback, useRef, useState } from 'react';
import { ApiError, apiGet } from '../api/client';
import type { Listing, Subscription } from '../api/types';
import { showPremiumPrompt } from '../hooks/usePremiumPrompt';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import ContractModal from './ContractModal';
import Icon from './Icon';
import Modal from './Modal';
import OpenInTelegram from './OpenInTelegram';
import PremiumBadge from './PremiumBadge';

interface ListingDocumentsProps {
  listing: Listing;
}

/**
 * «Документы» на странице объявления (только Premium): договор аренды в PDF.
 * Блок видят все. Анкета длинная, поэтому тариф проверяем до неё: без входа — окно входа
 * через Telegram, без Premium — общее окно «Подключить Premium». Окончательно решает бэкенд
 */
export default function ListingDocuments({ listing }: ListingDocumentsProps) {
  const { t } = useI18n();
  const ct = t.contract;
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [contractOpen, setContractOpen] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  const [checking, setChecking] = useState(false);
  // Premium уже подтверждён: второй раз подписку не спрашиваем
  const premium = useRef(false);
  // Стабильные ссылки: Modal перезапускает эффект (фокус) при смене onClose
  const closeContract = useCallback(() => setContractOpen(false), []);
  const closeLogin = useCallback(() => setLoginOpen(false), []);
  const askLogin = useCallback(() => setLoginOpen(true), []);

  const openContract = async () => {
    haptic('light');
    if (!authLoading && !isAuthenticated) {
      setLoginOpen(true);
      return;
    }
    if (!premium.current) {
      setChecking(true);
      try {
        const subscription = await apiGet<Subscription>('/api/subscription');
        if (!subscription.is_premium) {
          showPremiumPrompt('documents');
          return;
        }
        premium.current = true;
      } catch (error) {
        if (error instanceof ApiError && error.isUnauthorized) {
          setLoginOpen(true);
          return;
        }
        // Подписку узнать не удалось — анкету показываем, 402 придёт при отправке
      } finally {
        setChecking(false);
      }
    }
    setContractOpen(true);
  };

  return (
    <section
      className="listing-documents flex flex-col gap-4 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5"
      aria-labelledby="listing-documents-title"
    >
      <header className="listing-documents__header space-y-1">
        <h2
          id="listing-documents-title"
          className="flex flex-wrap items-center gap-2 text-lg font-semibold"
        >
          <Icon name="file" className="size-5 text-[var(--accent)]" />
          {ct.docs_title}
          <PremiumBadge />
        </h2>
        <p className="listing-documents__intro text-sm text-[var(--text-secondary)]">
          {ct.docs_intro}
        </p>
      </header>

      <button
        type="button"
        className="listing-documents__action flex min-h-12 w-full items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2.5 text-left text-sm font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-hover)] active:scale-[.98] disabled:opacity-70"
        aria-haspopup="dialog"
        aria-busy={checking}
        disabled={checking}
        onClick={() => void openContract()}
      >
        <Icon name="file" className="size-5 text-[var(--text-secondary)]" />
        <span className="min-w-0 flex-1 break-words">{ct.button}</span>
        {checking ? (
          <span className="spinner" aria-hidden="true" />
        ) : (
          <Icon name="chevron" className="size-4 text-[var(--text-secondary)]" />
        )}
      </button>

      <ContractModal
        open={contractOpen}
        listing={listing}
        onClose={closeContract}
        onLogin={askLogin}
      />
      <Modal open={loginOpen} title={ct.title} onClose={closeLogin}>
        <OpenInTelegram plain />
      </Modal>
    </section>
  );
}
