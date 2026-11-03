import { useEffect, useState } from 'react';
import type { CostMonth, ListingCosts as Costs, ListingId } from '../api/types';
import { useApi } from '../hooks/useApi';
import {
  DEPOSIT_CHOICES,
  FEE_CHOICES,
  MONTHS_MAX,
  PEOPLE_MAX,
  PEOPLE_MIN,
  costsApiPath,
  initialCostSettings,
  rememberCostSettings,
  startChoices,
  type CostSettings,
} from '../lib/costs';
import { fill, fillVars, formatMonth, formatNumber, formatPrice, plural } from '../lib/format';
import { haptic, isInTelegram } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import type { Strings } from '../i18n/strings';
import OpenInTelegram from './OpenInTelegram';
import PillGroup from './PillGroup';
import SelectField from './SelectField';

interface ListingCostsProps {
  listingId: ListingId;
}

type CostStrings = Strings['listing']['costs'];

const LEGEND_CLASS = 'mb-2 text-sm font-medium';
const ROW_CLASS = 'flex items-baseline justify-between gap-3';
const STEP_CLASS =
  'listing-costs__step inline-flex size-10 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface)] text-lg font-semibold transition-colors hover:bg-[var(--surface-hover)] active:scale-[.95] disabled:opacity-40';

/** Название статьи на языке интерфейса; незнакомая статья — как прислал сервер */
function itemTitle(code: string, ct: CostStrings, fallback: Costs['items']): string {
  return (
    (ct.items as Record<string, string>)[code] ??
    fallback.find((item) => item.code === code)?.title ??
    code
  );
}

/**
 * «Полная стоимость» помесячной аренды: при въезде, в среднем в месяц, за весь срок и
 * коммунальные по месяцам. Параметры меняют запрос; пока считается новый вариант, на экране
 * остаются прежние суммы. Нужен вход через Telegram (сервер отвечает 401 без initData)
 */
export default function ListingCosts({ listingId }: ListingCostsProps) {
  const { lang, t } = useI18n();
  const ct = t.listing.costs;
  const [settings, setSettings] = useState<CostSettings>(initialCostSettings);
  const inTelegram = isInTelegram();
  const { data, error, loading, reload } = useApi<Costs>(
    inTelegram ? costsApiPath(listingId, settings) : null,
  );
  // Прошлый ответ — пока новый в пути, чтобы суммы не мигали скелетоном
  const [shown, setShown] = useState<Costs>();
  useEffect(() => {
    if (data) setShown(data);
  }, [data]);

  // Другая валюта или квартира пропала — блока нет; 401 — предлагаем войти
  const needLogin = !inTelegram || error?.isUnauthorized === true;
  if (error && !needLogin && (error.status === 400 || error.isNotFound)) return null;

  const change = (patch: Partial<CostSettings>) => {
    setSettings((current) => {
      const next = { ...current, ...patch };
      rememberCostSettings(next);
      return next;
    });
  };

  const costs = data ?? shown;
  const busy = loading && Boolean(costs);

  return (
    <section
      className="listing-costs space-y-4 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5"
      aria-labelledby="listing-costs-title"
    >
      <header className="listing-costs__header space-y-1">
        <h2 id="listing-costs-title" className="text-lg font-semibold">
          {ct.title}
        </h2>
        <p className="m-0 text-sm text-[var(--text-secondary)]">{ct.intro}</p>
      </header>

      {needLogin ? (
        <OpenInTelegram plain />
      ) : (
        <>
          {costs ? (
            <div
              className={`listing-costs__result space-y-4 transition-opacity ${busy ? 'opacity-60' : ''}`}
              aria-busy={busy}
              aria-live="polite"
            >
              <CostSummary costs={costs} ct={ct} />
              {costs.agent_listing && (
                <p className="listing-costs__agent m-0 rounded-[var(--radius-md)] bg-[var(--surface-hover)] px-3 py-2 text-sm font-medium">
                  {ct.agent_hint}
                </p>
              )}
            </div>
          ) : error ? (
            <p className="listing-costs__error m-0 text-sm text-[var(--text-secondary)]">
              {ct.error}{' '}
              <button
                type="button"
                className="font-semibold text-[var(--text-primary)] underline underline-offset-2"
                onClick={() => {
                  haptic('light');
                  reload();
                }}
              >
                {t.listing.retry}
              </button>
            </p>
          ) : (
            <div
              className="listing-costs__skeleton h-44 animate-pulse rounded-[var(--radius-md)] bg-[var(--surface-hover)]"
              aria-hidden="true"
            />
          )}

          <CostControls settings={settings} onChange={change} ct={ct} />

          {costs && !costs.utilities_included && costs.monthly.length > 0 && (
            <CostMonths costs={costs} ct={ct} />
          )}

          {costs && (
            <footer className="listing-costs__note space-y-1 text-xs text-[var(--text-secondary)]">
              <p className="m-0">{fill(ct.note, costs.range_percent)}</p>
              {costs.rent_currency !== 'GEL' && (
                <p className="m-0">
                  {fillVars(ct.rate, {
                    symbol: formatPrice(1, costs.rent_currency).replace(/^1\s*/, ''),
                    rate: formatNumber(costs.exchange_rate, lang),
                  })}
                </p>
              )}
            </footer>
          )}
        </>
      )}
    </section>
  );
}

/** Три суммы: при въезде (с расшифровкой), в среднем в месяц, за весь срок */
function CostSummary({ costs, ct }: { costs: Costs; ct: CostStrings }) {
  const { lang } = useI18n();
  const first = costs.first_month;
  // Нулевые залог и комиссию не расписываем; коммунальные — если не включены в аренду
  const parts = [
    { label: ct.rent, value: first.rent, show: true },
    { label: ct.deposit, value: first.deposit, show: first.deposit > 0 },
    { label: ct.fee, value: first.agency_fee, show: first.agency_fee > 0 },
    { label: ct.utilities, value: first.utilities, show: !costs.utilities_included },
  ].filter((part) => part.show);

  return (
    <dl className="listing-costs__summary m-0 space-y-3">
      <div className="listing-costs__move-in space-y-1.5">
        <div className={ROW_CLASS}>
          <dt className="font-semibold">{ct.move_in}</dt>
          <dd className="m-0 text-xl font-bold tracking-tight">{formatPrice(first.total)}</dd>
        </div>
        <dd className="m-0">
          <ul className="listing-costs__parts m-0 list-none space-y-0.5 p-0 text-sm text-[var(--text-secondary)]">
            {parts.map((part) => (
              <li key={part.label} className={ROW_CLASS}>
                <span>{part.label}</span>
                <span className="tabular-nums">{formatPrice(part.value)}</span>
              </li>
            ))}
          </ul>
        </dd>
      </div>

      <div className="listing-costs__average space-y-0.5 border-t border-[var(--border)] pt-3">
        <div className={ROW_CLASS}>
          <dt className="font-semibold">{ct.average}</dt>
          <dd className="m-0 text-lg font-bold">{formatPrice(costs.average_month)}</dd>
        </div>
        <dd className="m-0 text-sm text-[var(--text-secondary)]">
          {costs.utilities_included
            ? ct.included
            : fill(ct.average_utilities, formatPrice(costs.average_utilities))}
        </dd>
      </div>

      <div className="listing-costs__period space-y-0.5 border-t border-[var(--border)] pt-3">
        <div className={ROW_CLASS}>
          <dt className="font-semibold">{plural(ct.period, costs.period_months, lang)}</dt>
          <dd className="m-0 text-lg font-bold">{formatPrice(costs.period_total)}</dd>
        </div>
        <dd className="m-0 text-sm text-[var(--text-secondary)]">{ct.period_hint}</dd>
      </div>
    </dl>
  );
}

interface CostControlsProps {
  settings: CostSettings;
  onChange: (patch: Partial<CostSettings>) => void;
  ct: CostStrings;
}

/** Параметры расчёта: люди, срок, месяц въезда, залог, комиссия, коммунальные в аренде */
function CostControls({ settings, onChange, ct }: CostControlsProps) {
  const { lang } = useI18n();
  const months = Array.from({ length: MONTHS_MAX }, (_, index) => index + 1);
  const step = (delta: number) => {
    haptic('selection');
    onChange({ people: settings.people + delta });
  };

  return (
    <fieldset className="listing-costs__settings m-0 min-w-0 space-y-4 border-0 border-t border-[var(--border)] p-0 pt-4">
      <legend className="float-left mb-3 w-full text-base font-semibold">{ct.settings}</legend>

      <div className="listing-costs__people clear-both flex items-center justify-between gap-3">
        <span id="listing-costs-people" className="text-sm font-medium">
          {ct.people}
        </span>
        <div
          className="flex items-center gap-3"
          role="group"
          aria-labelledby="listing-costs-people"
        >
          <button
            type="button"
            className={STEP_CLASS}
            aria-label={ct.fewer}
            disabled={settings.people <= PEOPLE_MIN}
            onClick={() => step(-1)}
          >
            −
          </button>
          <output
            className="min-w-6 text-center text-lg font-semibold tabular-nums"
            aria-live="polite"
          >
            {settings.people}
          </output>
          <button
            type="button"
            className={STEP_CLASS}
            aria-label={ct.more}
            disabled={settings.people >= PEOPLE_MAX}
            onClick={() => step(1)}
          >
            +
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <SelectField
          label={ct.months}
          value={String(settings.months)}
          options={months.map((n) => ({
            value: String(n),
            label: plural(ct.months_value, n, lang),
          }))}
          onChange={(value) => onChange({ months: Number(value) })}
        />
        <SelectField
          label={ct.start}
          value={settings.start}
          options={startChoices().map((month) => ({
            value: month,
            label: formatMonth(month, lang),
          }))}
          onChange={(value) => onChange({ start: value })}
        />
      </div>

      <PillGroup
        legend={ct.deposit}
        legendClassName={LEGEND_CLASS}
        options={DEPOSIT_CHOICES.map((n) => ({
          value: n,
          label: n === 0 ? ct.no_deposit : plural(ct.months_value, n, lang),
        }))}
        selected={[settings.deposit]}
        onToggle={(value) => onChange({ deposit: value })}
      />

      <PillGroup
        legend={ct.fee}
        legendClassName={LEGEND_CLASS}
        options={FEE_CHOICES.map((n) => ({ value: n, label: `${n}%` }))}
        selected={[settings.fee]}
        onToggle={(value) => onChange({ fee: value })}
        compact
      />

      <label className="listing-costs__included flex min-h-11 cursor-pointer items-center gap-3 text-sm font-medium">
        <input
          type="checkbox"
          className="size-5 shrink-0 accent-[var(--primary)]"
          checked={settings.utilitiesIncluded}
          onChange={(event) => {
            haptic('selection');
            onChange({ utilitiesIncluded: event.target.checked });
          }}
        />
        {ct.included}
      </label>
    </fieldset>
  );
}

/**
 * Коммунальные по месяцам — горизонтальные полосы одного цвета, длина от самого дорогого
 * месяца. Нажатие на месяц раскрывает статьи
 */
function CostMonths({ costs, ct }: { costs: Costs; ct: CostStrings }) {
  const { lang } = useI18n();
  const max = Math.max(1, ...costs.monthly.map((month) => month.utilities));

  return (
    <section
      className="listing-costs__months space-y-2 border-t border-[var(--border)] pt-4"
      aria-labelledby="listing-costs-months"
    >
      <header className="space-y-0.5">
        <h3 id="listing-costs-months" className="text-base font-semibold">
          {ct.monthly}
        </h3>
        <p className="m-0 text-xs text-[var(--text-secondary)]">{ct.monthly_hint}</p>
      </header>
      <ul className="m-0 list-none space-y-0.5 p-0">
        {costs.monthly.map((month, index) => (
          <li key={month.month}>
            <CostMonthRow
              month={month}
              // Год — у первого месяца и у каждого января
              label={formatMonth(month.month, lang, {
                short: true,
                withYear: index === 0 || month.month.endsWith('-01'),
              })}
              width={(month.utilities / max) * 100}
              costs={costs}
              ct={ct}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

interface CostMonthRowProps {
  month: CostMonth;
  label: string;
  /** Длина полосы, % от самого дорогого месяца */
  width: number;
  costs: Costs;
  ct: CostStrings;
}

function CostMonthRow({ month, label, width, costs, ct }: CostMonthRowProps) {
  const items = Object.entries(month.items).filter(
    (entry): entry is [string, number] => typeof entry[1] === 'number',
  );

  return (
    <details className="listing-costs__month group rounded-[var(--radius-sm)]">
      <summary className="grid min-h-9 cursor-pointer list-none grid-cols-[6rem_minmax(0,1fr)_4.5rem] items-center gap-2 rounded-[var(--radius-sm)] px-1 text-sm hover:bg-[var(--surface-hover)] [&::-webkit-details-marker]:hidden">
        <span className="truncate text-[var(--text-secondary)]">{label}</span>
        <span
          className="h-3 overflow-hidden rounded-full bg-[var(--surface-hover)]"
          aria-hidden="true"
        >
          <span
            className="listing-costs__bar block h-full rounded-full bg-[var(--primary)]"
            style={{ width: `${Math.max(width, 2)}%` }}
          />
        </span>
        <span className="text-right font-medium tabular-nums">{formatPrice(month.utilities)}</span>
      </summary>
      <ul className="m-0 mb-2 ml-[6.25rem] list-none space-y-0.5 p-0 pr-1 text-xs text-[var(--text-secondary)]">
        {items.map(([code, value]) => (
          <li key={code} className={ROW_CLASS}>
            <span>{itemTitle(code, ct, costs.items)}</span>
            <span className="tabular-nums">{formatPrice(value)}</span>
          </li>
        ))}
        <li className={`${ROW_CLASS} font-medium text-[var(--text-primary)]`}>
          <span>{ct.month_total}</span>
          <span className="tabular-nums">{formatPrice(month.total)}</span>
        </li>
      </ul>
    </details>
  );
}
