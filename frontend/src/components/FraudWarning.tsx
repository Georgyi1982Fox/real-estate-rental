import { useId, useState } from 'react';
import { Link } from 'react-router-dom';
import type { FraudLevel, ListingId, ListingRisk } from '../api/types';
import { useApi } from '../hooks/useApi';
import { fraudReasonTexts, riskReasonItems } from '../lib/fraud';
import { haptic, isInTelegram } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import RiskChecklist from './RiskChecklist';

interface FraudWarningProps {
  listingId: ListingId;
  level: FraudLevel;
  reasons: string[];
}

/**
 * Блок-предупреждение на странице объявления: warning — жёлтый, high — красный.
 * В Telegram причины прячутся под кнопку «Почему?» (GET /api/listings/{id}/risk):
 * с Premium — объяснения и «Что проверить до встречи», без него — названия причин
 * и ссылка на Premium. Вне Telegram (401) и при ошибке причины показаны списком, как раньше.
 * Объявление без подозрений: для Premium — свёрнутый блок «Как безопасно снять квартиру».
 */
export default function FraudWarning({ listingId, level, reasons }: FraudWarningProps) {
  const { lang, t } = useI18n();
  const ft = t.listing.fraud;
  const detailsId = useId();
  const [open, setOpen] = useState(false);
  // lang в адресе: тексты приходят на языке пользователя, сменили язык — запрашиваем заново
  const risk = useApi<ListingRisk>(
    isInTelegram() ? `/api/listings/${encodeURIComponent(listingId)}/risk?lang=${lang}` : null,
  );
  const checklist = (risk.data?.checklist ?? []).filter(Boolean);

  if (level === 'none') {
    if (checklist.length === 0) return null;
    return (
      <details className="safety-tips group rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] text-sm leading-5">
        <summary className="safety-tips__summary flex min-h-12 cursor-pointer list-none items-center gap-3 rounded-[var(--radius-md)] px-4 py-3 font-semibold hover:bg-[var(--surface-hover)] [&::-webkit-details-marker]:hidden">
          <Icon name="shield" className="size-5 text-[var(--text-secondary)]" />
          <span className="min-w-0 flex-1">{ft.safe_title}</span>
          <Icon
            name="chevron"
            className="size-4 text-[var(--text-secondary)] transition-transform duration-200 group-open:rotate-90"
          />
        </summary>
        <div className="safety-tips__body px-4 pb-4 text-[var(--text-secondary)]">
          <RiskChecklist items={checklist} label={ft.safe_title} />
        </div>
      </details>
    );
  }

  const isHigh = level === 'high';
  const ownTexts = fraudReasonTexts(reasons, ft.reasons);
  const items = risk.data ? riskReasonItems(risk.data.reasons, reasons, ft.reasons) : [];
  const hasDetails =
    items.length > 0 || checklist.length > 0 || Boolean(risk.data?.premium_required);

  return (
    <aside
      className={`fraud-warning fraud-warning--${level} flex gap-3 rounded-[var(--radius-md)] border p-4 text-sm leading-5 ${
        isHigh
          ? 'border-[var(--danger-border)] bg-[var(--danger-bg)] text-[var(--danger-text)]'
          : 'border-[var(--warning-border)] bg-[var(--warning-bg)] text-[var(--warning-text)]'
      }`}
      aria-labelledby="fraud-warning-title"
    >
      <Icon name={isHigh ? 'ban' : 'alert'} className="fraud-warning__icon mt-0.5 size-5" />
      <div className="fraud-warning__body min-w-0 flex-1 space-y-2 break-words">
        <h2
          id="fraud-warning-title"
          className="fraud-warning__title text-base font-semibold leading-6"
        >
          {isHigh ? ft.high : ft.warning}
        </h2>
        <p className="fraud-warning__advice">{ft.advice}</p>

        {/* Разбор недоступен (браузер, ошибка) — причины списком, как в значке */}
        {!risk.loading && !risk.data && ownTexts.length > 0 && (
          <ul
            className="fraud-warning__reasons list-disc space-y-1 pl-5"
            aria-label={ft.reasons_label}
          >
            {ownTexts.map((text) => (
              <li key={text}>{text}</li>
            ))}
          </ul>
        )}

        {hasDetails && (
          <>
            <button
              type="button"
              className="fraud-warning__why -ml-1 inline-flex min-h-9 items-center gap-1 rounded-[var(--radius-sm)] px-1 font-semibold underline underline-offset-2"
              aria-expanded={open}
              aria-controls={detailsId}
              onClick={() => {
                haptic('light');
                setOpen((value) => !value);
              }}
            >
              {ft.why}
              <Icon
                name="chevron"
                className={`size-4 transition-transform duration-200 ${open ? '-rotate-90' : 'rotate-90'}`}
              />
            </button>

            <div id={detailsId} className="fraud-warning__details space-y-3" hidden={!open}>
              {items.length > 0 && (
                <ul className="fraud-warning__reasons space-y-2" aria-label={ft.reasons_label}>
                  {items.map((item) => (
                    <li key={item.key} className="fraud-warning__reason">
                      <strong className="font-semibold">{item.title}</strong>
                      {item.explanation && <span className="block">{item.explanation}</span>}
                    </li>
                  ))}
                </ul>
              )}

              {checklist.length > 0 && (
                <section className="fraud-warning__checklist space-y-2">
                  <h3 className="font-semibold">{ft.checklist}</h3>
                  <RiskChecklist items={checklist} label={ft.checklist} />
                </section>
              )}

              {risk.data?.premium_required && (
                <p className="fraud-warning__premium m-0">
                  <Link
                    to="/premium"
                    className="rounded-[var(--radius-sm)] font-semibold underline underline-offset-2"
                  >
                    {ft.premium_link}
                  </Link>
                </p>
              )}
            </div>
          </>
        )}
      </div>
    </aside>
  );
}
