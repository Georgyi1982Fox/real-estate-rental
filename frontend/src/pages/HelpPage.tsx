import Accordion from '../components/Accordion';
import ExternalLink from '../components/ExternalLink';
import Icon from '../components/Icon';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { botSectionUrl } from '../lib/config';
import { useI18n } from '../providers/I18nProvider';

/** Помощь: что умеет bina.ai и частые вопросы */
export default function HelpPage() {
  const { t } = useI18n();
  const ht = t.help;

  useDocumentTitle(`${ht.page_title} — bina.ai`);
  useTelegramBackButton('/');

  return (
    <section
      className="help mx-auto flex w-full max-w-2xl flex-col gap-6 py-2 sm:py-4"
      aria-labelledby="help-title"
    >
      <header className="help__header flex flex-col gap-2">
        <h1 id="help-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
          {ht.page_title}
        </h1>
        <p className="text-sm leading-relaxed text-[var(--text-secondary)] sm:text-base">
          {ht.intro}
        </p>
      </header>

      <section className="help__faq flex flex-col gap-3" aria-labelledby="help-faq-title">
        <h2 id="help-faq-title" className="text-lg font-semibold">
          {ht.faq}
        </h2>
        <Accordion
          items={ht.items.map((item) => ({ title: item.q, text: item.a }))}
          openIndex={0}
        />
      </section>

      <footer className="help__support flex flex-col items-start gap-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-[var(--text-secondary)]">{ht.no_answer}</p>
        <ExternalLink
          href={botSectionUrl('support')}
          className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] hover:bg-[var(--primary-hover)] active:scale-[.98]"
        >
          <Icon name="message" />
          {t.hub.tiles.support.title}
        </ExternalLink>
      </footer>
    </section>
  );
}
