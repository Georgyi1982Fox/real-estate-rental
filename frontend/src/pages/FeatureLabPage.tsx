// Временная страница «Проверка функций» (только для владельца): кнопки для новых функций
// бэкенда (TASK-101…108), пока у них нет своих экранов. Удалить, когда будут FRONTEND-023…029.
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, apiGet, apiPost } from '../api/client';
import type { Lang } from '../i18n/strings';
import type { Listing, ListingsPage } from '../api/types';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { tr } from '../lib/format';
import { openLink } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

const TEXTS = {
  ru: {
    title: '🧪 Проверка функций',
    intro: 'Временная страница: новые функции без дизайна. Видна только вам.',
    owner_only: 'Эта страница только для владельца (ADMIN_TELEGRAM_IDS).',
    listing: 'Объявление для проверки',
    run: 'Проверить',
    send: 'Отправить',
    loading: 'Загрузка…',
    error: 'Ошибка',
    costs: '💰 Калькулятор стоимости',
    district: '📍 Информация о районе',
    map: '🗺 Место на карте',
    compare: '⚖️ Сравнение (отметьте 2–3 объявления)',
    contract: '📄 Договор аренды (PDF придёт в Telegram)',
    acceptance: '✅ Акт приёмки (PDF придёт в Telegram)',
    complaint: '⚠️ Жалоба на объявление',
    invite: '🎁 Пригласить друга',
    landlord: 'Хозяин',
    tenant: 'Арендатор',
    address: 'Адрес',
    start: 'Дата начала',
    months: 'Месяцев',
    reason: 'Причина',
    move_in: 'При въезде',
    per_month: 'В среднем в месяц',
    total: 'За 12 месяцев',
    minutes: 'мин до центра',
    metro_yes: 'есть метро',
    metro_no: 'без метро',
    listings: 'объявлений в поиске',
    rooms: 'комн.',
    exact: 'Точная точка',
    approx: 'Примерно (центр района)',
    none: 'Место неизвестно',
    sent: '✅ Отправлено в чат с ботом',
    best: 'лучшее',
    copy: 'Скопировать',
    open: 'Открыть',
  },
  en: {
    title: '🧪 Feature check',
    intro: 'Temporary page: new features without design. Visible only to you.',
    owner_only: 'This page is for the owner only (ADMIN_TELEGRAM_IDS).',
    listing: 'Listing to test',
    run: 'Check',
    send: 'Send',
    loading: 'Loading…',
    error: 'Error',
    costs: '💰 Cost calculator',
    district: '📍 District info',
    map: '🗺 Location on the map',
    compare: '⚖️ Compare (tick 2–3 listings)',
    contract: '📄 Lease agreement (PDF arrives in Telegram)',
    acceptance: '✅ Handover report (PDF arrives in Telegram)',
    complaint: '⚠️ Report a listing',
    invite: '🎁 Invite a friend',
    landlord: 'Landlord',
    tenant: 'Tenant',
    address: 'Address',
    start: 'Start date',
    months: 'Months',
    reason: 'Reason',
    move_in: 'At move-in',
    per_month: 'Average month',
    total: 'For 12 months',
    minutes: 'min to the centre',
    metro_yes: 'metro nearby',
    metro_no: 'no metro',
    listings: 'listings in search',
    rooms: 'rooms',
    exact: 'Exact point',
    approx: 'Approximate (district centre)',
    none: 'Location unknown',
    sent: '✅ Sent to your chat with the bot',
    best: 'best',
    copy: 'Copy',
    open: 'Open',
  },
  ka: {
    title: '🧪 ფუნქციების შემოწმება',
    intro: 'დროებითი გვერდი: ახალი ფუნქციები დიზაინის გარეშე. ჩანს მხოლოდ თქვენთვის.',
    owner_only: 'ეს გვერდი მხოლოდ მფლობელისთვისაა (ADMIN_TELEGRAM_IDS).',
    listing: 'განცხადება შესამოწმებლად',
    run: 'შემოწმება',
    send: 'გაგზავნა',
    loading: 'იტვირთება…',
    error: 'შეცდომა',
    costs: '💰 ღირებულების კალკულატორი',
    district: '📍 ინფორმაცია უბანზე',
    map: '🗺 ადგილი რუკაზე',
    compare: '⚖️ შედარება (მონიშნეთ 2–3 განცხადება)',
    contract: '📄 ქირავნობის ხელშეკრულება (PDF მოვა Telegram-ში)',
    acceptance: '✅ მიღება-ჩაბარების აქტი (PDF მოვა Telegram-ში)',
    complaint: '⚠️ საჩივარი განცხადებაზე',
    invite: '🎁 მეგობრის მოწვევა',
    landlord: 'გამქირავებელი',
    tenant: 'დამქირავებელი',
    address: 'მისამართი',
    start: 'დაწყების თარიღი',
    months: 'თვე',
    reason: 'მიზეზი',
    move_in: 'შესვლისას',
    per_month: 'საშუალოდ თვეში',
    total: '12 თვეში',
    minutes: 'წთ ცენტრამდე',
    metro_yes: 'მეტრო ახლოსაა',
    metro_no: 'მეტროს გარეშე',
    listings: 'განცხადება ძებნაში',
    rooms: 'ოთახი',
    exact: 'ზუსტი წერტილი',
    approx: 'მიახლოებით (უბნის ცენტრი)',
    none: 'ადგილი უცნობია',
    sent: '✅ გაიგზავნა ბოტთან ჩატში',
    best: 'საუკეთესო',
    copy: 'კოპირება',
    open: 'გახსნა',
  },
} satisfies Record<Lang, Record<string, string>>;

type Texts = (typeof TEXTS)['ru'];

const CARD =
  'rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[var(--shadow-sm)]';
const BUTTON =
  'inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] bg-[var(--primary)] px-4 text-sm font-semibold text-white disabled:opacity-50';
const INPUT =
  'w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm';

interface Result {
  loading?: boolean;
  error?: string;
  content?: ReactNode;
}

function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.status} ${error.code ?? error.message}`;
  return String(error);
}

/** Карточка функции: заголовок, поля, кнопка и результат */
function Section({
  title,
  label,
  onRun,
  result,
  disabled,
  children,
}: {
  title: string;
  label: string;
  onRun: () => void;
  result: Result;
  disabled?: boolean;
  children?: ReactNode;
}) {
  return (
    <article className={CARD}>
      <h2 className="mb-3 text-base font-semibold text-[var(--text-primary)]">{title}</h2>
      {children && <div className="mb-3 grid gap-2">{children}</div>}
      <button type="button" className={BUTTON} onClick={onRun} disabled={disabled || result.loading}>
        {label}
      </button>
      {result.loading && <p className="mt-3 text-sm text-[var(--text-secondary)]">…</p>}
      {result.error && <p className="mt-3 text-sm text-red-600">{result.error}</p>}
      {result.content && <div className="mt-3 text-sm text-[var(--text-primary)]">{result.content}</div>}
    </article>
  );
}

function useRunner() {
  const [results, setResults] = useState<Record<string, Result>>({});
  const run = async (key: string, action: () => Promise<ReactNode>) => {
    setResults((current) => ({ ...current, [key]: { loading: true } }));
    try {
      const content = await action();
      setResults((current) => ({ ...current, [key]: { content } }));
    } catch (error) {
      setResults((current) => ({ ...current, [key]: { error: errorText(error) } }));
    }
  };
  return { results, run, get: (key: string): Result => results[key] ?? {} };
}

export default function FeatureLabPage() {
  const { lang } = useI18n();
  const x: Texts = TEXTS[lang];
  const navigate = useNavigate();
  useDocumentTitle(`${x.title} — Bina.ai`);

  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [selected, setSelected] = useState<string>('');
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [form, setForm] = useState({
    landlord: 'Giorgi Beridze',
    tenant: 'Anna Smith',
    address: '',
    start: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
    months: '12',
  });
  const [reasons, setReasons] = useState<{ code: string; title: string }[]>([]);
  const [reason, setReason] = useState('fraud');
  const { run, get } = useRunner();

  useEffect(() => {
    apiGet<{ is_admin?: boolean }>('/api/me')
      .then((me) => setIsAdmin(Boolean(me.is_admin)))
      .catch(() => setIsAdmin(false));
    apiGet<ListingsPage>('/api/listings?page=1&per_page=20')
      .then((page) => {
        setListings(page.items);
        if (page.items[0]) setSelected(String(page.items[0].id));
      })
      .catch(() => setListings([]));
    apiGet<{ code: string; title: string }[]>('/api/complaints/reasons')
      .then(setReasons)
      .catch(() => setReasons([]));
  }, [lang]);

  const listing = useMemo(
    () => listings.find((item) => String(item.id) === selected),
    [listings, selected],
  );
  const listingTitle = (item: Listing) =>
    `${tr(item.title, lang).slice(0, 50)} — ${item.price} ${item.currency}`;

  if (isAdmin === null) return <p className="p-4 text-sm">{x.loading}</p>;
  if (!isAdmin) return <p className="p-4 text-sm">{x.owner_only}</p>;

  const id = selected;
  const line = (label: string, value: ReactNode) => (
    <p>
      <span className="text-[var(--text-secondary)]">{label}: </span>
      <b>{value}</b>
    </p>
  );

  return (
    <section className="mx-auto grid w-full max-w-3xl gap-4 p-4">
      <header>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">{x.title}</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">{x.intro}</p>
      </header>

      <article className={CARD}>
        <label className="grid gap-2 text-sm font-semibold">
          {x.listing}
          <select className={INPUT} value={selected} onChange={(e) => setSelected(e.target.value)}>
            {listings.map((item) => (
              <option key={String(item.id)} value={String(item.id)}>
                {listingTitle(item)}
              </option>
            ))}
          </select>
        </label>
      </article>

      <Section
        title={x.costs}
        label={x.run}
        disabled={!id}
        result={get('costs')}
        onRun={() =>
          void run('costs', async () => {
            const c = await apiGet<{
              first_month: { total: number };
              average_month: number;
              period_total: number;
              monthly: { month: string; utilities: number }[];
              note: string;
            }>(`/api/listings/${id}/costs`);
            return (
              <>
                {line(x.move_in, `${c.first_month.total} ₾`)}
                {line(x.per_month, `${c.average_month} ₾`)}
                {line(x.total, `${c.period_total} ₾`)}
                <p className="mt-2 text-xs text-[var(--text-secondary)]">
                  {c.monthly.map((m) => `${m.month}: ${m.utilities} ₾`).join(' · ')}
                </p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">{c.note}</p>
              </>
            );
          })
        }
      />

      <Section
        title={x.district}
        label={x.run}
        disabled={!listing}
        result={get('district')}
        onRun={() =>
          void run('district', async () => {
            const d = await apiGet<{
              name: string;
              minutes_to_center: number | null;
              metro: boolean | null;
              about: string | null;
              tags: { title: string }[];
              listings: number;
              median_rent: { rooms: number; price: number }[];
              note: string;
            }>(`/api/districts/${listing?.district}`);
            return (
              <>
                <p className="font-semibold">{d.name}</p>
                <p>
                  {d.minutes_to_center != null && `~${d.minutes_to_center} ${x.minutes} · `}
                  {d.metro == null ? '' : d.metro ? x.metro_yes : x.metro_no} · {d.listings}{' '}
                  {x.listings}
                </p>
                {d.about && <p className="mt-1">{d.about}</p>}
                <p className="mt-1">{d.tags.map((tag) => tag.title).join(' · ')}</p>
                <p className="mt-1">
                  {d.median_rent.map((m) => `${m.rooms} ${x.rooms}: ~${m.price} ₾`).join(' · ')}
                </p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">{d.note}</p>
              </>
            );
          })
        }
      />

      <Section
        title={x.map}
        label={x.run}
        disabled={!id}
        result={get('map')}
        onRun={() =>
          void run('map', async () => {
            const loc = await apiGet<{
              precision: 'exact' | 'district' | 'none';
              latitude: number | null;
              longitude: number | null;
              district: string | null;
              links: { google: string; yandex: string; osm: string } | null;
            }>(`/api/listings/${id}/location`);
            const precision = { exact: x.exact, district: x.approx, none: x.none }[loc.precision];
            return (
              <>
                <p>
                  {precision}
                  {loc.district ? ` — ${loc.district}` : ''}
                </p>
                {loc.links && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(['google', 'yandex', 'osm'] as const).map((name) => (
                      <button
                        key={name}
                        type="button"
                        className={BUTTON}
                        onClick={() => openLink(loc.links![name], navigate)}
                      >
                        {x.open} {name === 'osm' ? 'OpenStreetMap' : name === 'google' ? 'Google Maps' : 'Яндекс'}
                      </button>
                    ))}
                  </div>
                )}
              </>
            );
          })
        }
      />

      <Section
        title={x.compare}
        label={x.run}
        disabled={compareIds.length < 2}
        result={get('compare')}
        onRun={() =>
          void run('compare', async () => {
            const table = await apiGet<{
              rows: { code: string; title: string }[];
              items: Record<string, unknown>[];
              best: Record<string, string[]>;
            }>(`/api/listings/compare?ids=${compareIds.join(',')}`);
            const shown = table.rows.filter((row) => row.code !== 'features');
            return (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-xs">
                  <tbody>
                    {shown.map((row) => (
                      <tr key={row.code} className="border-t border-[var(--border)]">
                        <th className="py-1 pr-2 text-left font-normal text-[var(--text-secondary)]">
                          {row.title}
                        </th>
                        {table.items.map((item) => {
                          const itemId = String((item.listing as { id: string }).id);
                          const best = table.best[row.code]?.includes(itemId);
                          return (
                            <td key={itemId} className={`py-1 pr-2 ${best ? 'font-bold text-green-700' : ''}`}>
                              {String(item[row.code] ?? '—')}
                              {best ? ` ✓ ${x.best}` : ''}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          })
        }
      >
        <div className="grid max-h-48 gap-1 overflow-y-auto">
          {listings.map((item) => {
            const itemId = String(item.id);
            const checked = compareIds.includes(itemId);
            return (
              <label key={itemId} className="flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={!checked && compareIds.length >= 3}
                  onChange={() =>
                    setCompareIds((ids) =>
                      checked ? ids.filter((value) => value !== itemId) : [...ids, itemId],
                    )
                  }
                />
                {listingTitle(item)}
              </label>
            );
          })}
        </div>
      </Section>

      <Section
        title={x.contract}
        label={x.send}
        disabled={!id}
        result={get('contract')}
        onRun={() =>
          void run('contract', async () => {
            await apiPost(`/api/listings/${id}/contract`, {
              landlord_name: form.landlord,
              tenant_name: form.tenant,
              address: form.address || undefined,
              start_date: form.start,
              months: Number(form.months) || 12,
              deposit: listing?.price ?? 0,
              delivery: 'chat',
            });
            return <p>{x.sent}</p>;
          })
        }
      >
        <input className={INPUT} placeholder={x.landlord} value={form.landlord} onChange={(e) => setForm({ ...form, landlord: e.target.value })} />
        <input className={INPUT} placeholder={x.tenant} value={form.tenant} onChange={(e) => setForm({ ...form, tenant: e.target.value })} />
        <input className={INPUT} placeholder={x.address} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
        <div className="grid grid-cols-2 gap-2">
          <input className={INPUT} type="date" aria-label={x.start} value={form.start} onChange={(e) => setForm({ ...form, start: e.target.value })} />
          <input className={INPUT} type="number" min={1} max={60} aria-label={x.months} value={form.months} onChange={(e) => setForm({ ...form, months: e.target.value })} />
        </div>
      </Section>

      <Section
        title={x.acceptance}
        label={x.send}
        disabled={!id}
        result={get('acceptance')}
        onRun={() =>
          void run('acceptance', async () => {
            const checklist = await apiGet<{ sections: { items: { code: string }[] }[] }>(
              '/api/documents/acceptance/checklist',
            );
            const codes = checklist.sections.flatMap((section) => section.items.map((item) => item.code));
            await apiPost('/api/documents/acceptance', {
              listing_id: id,
              landlord_name: form.landlord,
              tenant_name: form.tenant,
              address: form.address || undefined,
              items: codes.map((code, index) =>
                index === 1
                  ? { code, status: 'defect', comment: 'Scratch on the door' }
                  : { code, status: 'ok' },
              ),
              keys: 2,
              electricity: '12345',
              delivery: 'chat',
            });
            return <p>{x.sent}</p>;
          })
        }
      />

      <Section
        title={x.complaint}
        label={x.send}
        disabled={!id}
        result={get('complaint')}
        onRun={() =>
          void run('complaint', async () => {
            const answer = await apiPost<{ message: string }>(`/api/listings/${id}/complaints`, {
              reason,
            });
            return <p>{answer.message}</p>;
          })
        }
      >
        <select className={INPUT} aria-label={x.reason} value={reason} onChange={(e) => setReason(e.target.value)}>
          {reasons.map((item) => (
            <option key={item.code} value={item.code}>
              {item.title}
            </option>
          ))}
        </select>
      </Section>

      <Section
        title={x.invite}
        label={x.run}
        result={get('invite')}
        onRun={() =>
          void run('invite', async () => {
            const ref = await apiGet<{ link: string; invited: number; rewarded: number }>(
              '/api/referral',
            );
            return (
              <>
                <p className="break-all font-mono text-xs">{ref.link}</p>
                <p className="mt-1">
                  {ref.invited} / {ref.rewarded}
                </p>
                <button
                  type="button"
                  className={`${BUTTON} mt-2`}
                  onClick={() => void navigator.clipboard?.writeText(ref.link)}
                >
                  {x.copy}
                </button>
              </>
            );
          })
        }
      />
    </section>
  );
}
