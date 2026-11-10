import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { ListingId, PhotoReport } from '../api/types';
import { useApi } from '../hooks/useApi';
import { haptic, isInTelegram } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';
import RepairBadge, { isRepairLevel } from './RepairBadge';

interface ListingPhotoReportProps {
  listingId: ListingId;
}

// Без Premium и без разбора сервер отвечает быстро: скелетон — только если ответ задержался
// (Premium: AI смотрит фото до 30 с), чтобы блок не мигал перед 404
const SKELETON_DELAY_MS = 500;

/**
 * «Что видно на фото» (AI, TASK-114). Premium — проблемы и вывод; без Premium — уровень и
 * размытое приглашение в Premium. Нужен вход через Telegram: вне Telegram и при 401 блока
 * нет; 404 (фото нет или разбора ещё нет), 503, 429 и прочие ошибки — блок тихо скрыт
 */
export default function ListingPhotoReport({ listingId }: ListingPhotoReportProps) {
  const { lang, t } = useI18n();
  const rt = t.listing.repair;
  // ?lang= — вывод AI на языке интерфейса, даже если в профиле сохранён другой
  const { data, error, loading } = useApi<PhotoReport>(
    isInTelegram()
      ? `/api/listings/${encodeURIComponent(listingId)}/photo-report?lang=${lang}`
      : null,
  );
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (!loading) {
      setSlow(false);
      return;
    }
    const timer = window.setTimeout(() => setSlow(true), SKELETON_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [loading]);

  if (error || (!data && !(loading && slow))) return null;
  if (data && !isRepairLevel(data.level)) return null;

  return (
    <section
      className="listing-photo-report space-y-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5"
      aria-labelledby="listing-photo-report-title"
      aria-busy={!data}
    >
      <h2 id="listing-photo-report-title" className="text-lg font-semibold">
        {rt.title}
      </h2>

      {!data ? (
        <div className="listing-photo-report__pending space-y-2" role="status">
          <p className="m-0 flex items-center gap-2 text-sm text-[var(--text-secondary)]">
            <Icon name="sparkles" className="size-4" />
            {rt.thinking}
          </p>
          <div className="space-y-2" aria-hidden="true">
            <div className="h-3.5 w-2/5 animate-pulse rounded bg-[var(--surface-hover)]" />
            <div className="h-3.5 w-full animate-pulse rounded bg-[var(--surface-hover)]" />
            <div className="h-3.5 w-4/5 animate-pulse rounded bg-[var(--surface-hover)]" />
          </div>
        </div>
      ) : (
        <>
          <RepairBadge level={data.level} />
          {data.premium_required ? <PhotoReportLocked /> : <PhotoReportDetails report={data} />}
        </>
      )}
    </section>
  );
}

function PhotoReportDetails({ report }: { report: PhotoReport }) {
  const { t } = useI18n();
  const rt = t.listing.repair;
  const issueLabels = rt.issues as Record<string, string>;
  // Название проблемы — из наших строк по коду; незнакомый код — как прислал сервер
  const issues = report.issues
    .map((issue) => ({ code: issue.code, label: issueLabels[issue.code] ?? issue.label }))
    .filter((issue) => issue.label);
  const summary = report.summary.trim();

  return (
    <div className="listing-photo-report__details space-y-3">
      {issues.length > 0 ? (
        <ul className="listing-photo-report__issues space-y-2" aria-label={rt.issues_label}>
          {issues.map((issue) => (
            <li
              key={issue.code}
              className="listing-photo-report__issue flex items-start gap-2 text-sm leading-5"
            >
              <Icon name="alert" className="mt-0.5 size-4 shrink-0 text-[var(--promo-text)]" />
              <span className="min-w-0 break-words">{issue.label}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="listing-photo-report__clean m-0 flex items-start gap-2 text-sm leading-5">
          <Icon name="check" className="mt-0.5 size-4 shrink-0 text-[var(--success-text)]" />
          {rt.no_issues}
        </p>
      )}
      {summary && (
        <p className="listing-photo-report__summary m-0 whitespace-pre-line break-words text-sm leading-relaxed text-[var(--text-secondary)]">
          {summary}
        </p>
      )}
    </div>
  );
}

/** Размытый «разбор» вместо настоящего: текст под ним — только для вида, читать нечего */
function PhotoReportLocked() {
  const { t } = useI18n();
  const rt = t.listing.repair;
  const sample = [rt.issues.mold, rt.issues.cracks, rt.issues.old_appliances, rt.issues.worn_floor];

  return (
    <div className="listing-photo-report__locked relative overflow-hidden rounded-[var(--radius-md)] border border-[var(--border)]">
      <ul className="space-y-3 p-4 py-6 blur-[5px] select-none" aria-hidden="true">
        {sample.map((label) => (
          <li key={label} className="flex items-center gap-2 text-sm">
            <Icon name="alert" className="size-4 shrink-0" />
            {label}
          </li>
        ))}
      </ul>
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-[color-mix(in_srgb,var(--surface)_65%,transparent)] p-4 text-center">
        <Icon name="lock" className="size-5 shrink-0 text-[var(--text-secondary)]" />
        <p className="m-0 max-w-xs text-sm font-medium leading-5">{rt.locked}</p>
        <Link
          to="/premium"
          onClick={() => haptic('light')}
          className="listing-photo-report__premium inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-md)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--primary-hover)] active:scale-[.98]"
        >
          <Icon name="crown" className="size-4" />
          {rt.premium}
        </Link>
      </div>
    </div>
  );
}
