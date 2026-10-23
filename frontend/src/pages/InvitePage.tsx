import type { Referral } from '../api/types';
import ErrorState from '../components/ErrorState';
import Icon from '../components/Icon';
import OpenInTelegram from '../components/OpenInTelegram';
import StatTile from '../components/StatTile';
import { useApi } from '../hooks/useApi';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { useShareInvite } from '../hooks/useShareInvite';
import { useTelegramBackButton } from '../hooks/useTelegramBackButton';
import { fill, fillVars, plural } from '../lib/format';
import { REFERRAL_API } from '../lib/referral';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';

const CARD_CLASS =
  'rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)]';

/** Бэкенд не знает имя бота — ссылку не собрать */
const NOT_CONFIGURED = 503;

/**
 * «🎁 Пригласить друга» (FRONTEND-029): условия, своя ссылка, «Поделиться» и счётчики.
 * Цифры условий — только из ответа /api/referral, в текстах их нет
 */
export default function InvitePage() {
  const { t, lang } = useI18n();
  const rt = t.referral;
  const { user, loading: authLoading } = useAuth();
  const { data, error, loading, reload } = useApi<Referral>(user ? REFERRAL_API : null);
  const shareInvite = useShareInvite();
  const title = t.hub.tiles.invite.title;

  useDocumentTitle(`${title} — bina.ai`);
  useTelegramBackButton('/profile');

  if ((!user && !authLoading) || error?.isUnauthorized) {
    return (
      <section className="invite mx-auto w-full max-w-md py-6">
        <OpenInTelegram />
      </section>
    );
  }

  let body;
  if (error?.status === NOT_CONFIGURED) {
    body = (
      <p className="invite__unavailable rounded-[var(--radius-md)] bg-[var(--surface-hover)] p-4 text-center text-sm">
        {rt.unavailable}
      </p>
    );
  } else if (error) {
    body = <ErrorState compact onRetry={reload} />;
  } else if (loading || authLoading || !data) {
    body = (
      <div className="flex animate-pulse flex-col gap-4" aria-hidden="true">
        <span className="h-24 rounded-[var(--radius-lg)] bg-[var(--surface-hover)]" />
        <span className="h-12 rounded-[var(--radius-md)] bg-[var(--surface-hover)]" />
        <span className="grid grid-cols-2 gap-3">
          <span className="h-28 rounded-[var(--radius-lg)] bg-[var(--surface-hover)]" />
          <span className="h-28 rounded-[var(--radius-lg)] bg-[var(--surface-hover)]" />
        </span>
      </div>
    );
  } else {
    body = (
      <>
        <section className={`invite__terms ${CARD_CLASS}`} aria-labelledby="invite-terms-title">
          <h2 id="invite-terms-title" className="mb-3 text-lg font-semibold">
            {rt.terms_title}
          </h2>
          <ul className="flex flex-col gap-3 text-sm leading-relaxed">
            <li className="flex gap-3">
              <Icon name="gift" className="mt-0.5 size-5 shrink-0 text-[var(--tone-benefit)]" />
              <span>{fill(rt.friend_gets, data.friend_discount_percent)}</span>
            </li>
            <li className="flex gap-3">
              <Icon name="crown" className="mt-0.5 size-5 shrink-0 text-[var(--accent)]" />
              <span>
                {fillVars(rt.you_get, {
                  days: plural(t.premium.days, data.reward_days, lang),
                  limit: data.monthly_limit,
                })}
              </span>
            </li>
          </ul>
        </section>

        <section className="invite__link flex flex-col gap-3" aria-labelledby="invite-link-title">
          <h2 id="invite-link-title" className="text-lg font-semibold">
            {rt.link_title}
          </h2>
          {/* Ссылку можно выделить и скопировать вручную, если «Поделиться» не сработает */}
          <p className="invite__url m-0 select-all break-all rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 font-mono text-sm">
            {data.link}
          </p>
          <button
            type="button"
            className="invite__share inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-3 text-base font-semibold text-white shadow-[var(--shadow-md)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]"
            onClick={() => void shareInvite(data.link, rt.copied)}
          >
            <Icon name="forward" />
            {rt.share}
          </button>
        </section>

        <section className="invite__stats flex flex-col gap-3" aria-labelledby="invite-stats-title">
          <h2 id="invite-stats-title" className="text-lg font-semibold">
            {rt.stats_title}
          </h2>
          <ul className="grid grid-cols-2 gap-3">
            <li>
              <StatTile icon="users" label={rt.invited} value={data.invited} />
            </li>
            <li>
              <StatTile icon="crown" label={rt.rewarded} value={data.rewarded} />
            </li>
          </ul>
          <p className="m-0 text-sm text-[var(--text-secondary)]">
            {fillVars(rt.this_month, {
              used: data.rewarded_this_month,
              limit: data.monthly_limit,
            })}
          </p>
        </section>
      </>
    );
  }

  return (
    <section
      className="invite mx-auto flex w-full max-w-2xl flex-col gap-6 py-2 sm:py-4"
      aria-labelledby="invite-title"
      aria-busy={loading}
    >
      <header className="invite__hero flex flex-col items-center gap-3 pt-2 text-center">
        <span className="invite__icon inline-grid size-20 place-items-center rounded-full bg-[var(--tone-benefit)]/15 text-[var(--tone-benefit)] shadow-[var(--shadow-md)]">
          <Icon name="gift" className="size-10" />
        </span>
        <h1 id="invite-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
          {title}
        </h1>
        <p className="max-w-md text-sm text-[var(--text-secondary)] sm:text-base">{rt.subtitle}</p>
      </header>
      {body}
    </section>
  );
}
