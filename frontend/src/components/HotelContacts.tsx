import { useCallback, useState } from 'react';
import type { ReactNode } from 'react';
import { ApiError, apiGet } from '../api/client';
import type { Hotel, HotelContact } from '../api/types';
import { haptic } from '../lib/telegram';
import { useAuth } from '../providers/AuthProvider';
import { useI18n } from '../providers/I18nProvider';
import ExternalLink from './ExternalLink';
import Icon from './Icon';
import Modal from './Modal';
import OpenInTelegram from './OpenInTelegram';
import TelegramIcon from './TelegramIcon';

type ContactState = 'idle' | 'loading' | 'done' | 'error' | 'login';

const BUTTON_CLASS =
  'hotel-contacts__button inline-flex min-h-12 w-full min-w-0 items-center justify-center gap-2 rounded-[var(--radius-md)] px-4 py-3 text-center text-sm font-semibold transition-colors active:scale-[.98] disabled:opacity-70';
const PRIMARY_CLASS = `${BUTTON_CLASS} bg-[var(--primary)] text-white shadow-[var(--shadow-sm)] hover:bg-[var(--primary-hover)]`;
const SECONDARY_CLASS = `${BUTTON_CLASS} border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--surface-hover)]`;

interface HotelContactsProps {
  hotel: Pick<Hotel, 'id' | 'has_phone' | 'has_whatsapp' | 'has_telegram'>;
}

/**
 * «Позвонить», «WhatsApp», «Telegram» — по has_*. Контакты не лежат в разметке: первое
 * нажатие запрашивает их у бэкенда (GET /api/hotels/{id}/contact), после чего кнопки
 * становятся настоящими ссылками. Гостю без входа — «Войдите, чтобы увидеть контакты».
 *
 * Ссылками, а не переходом после ответа сервера: Telegram открывает внешние ссылки только
 * прямо в ответ на нажатие.
 */
export default function HotelContacts({ hotel }: HotelContactsProps) {
  const { t } = useI18n();
  const ht = t.hotels;
  const { user, loading: authLoading } = useAuth();
  const [state, setState] = useState<ContactState>('idle');
  const [contact, setContact] = useState<HotelContact>({});
  const [loginOpen, setLoginOpen] = useState(false);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const closeLogin = useCallback(() => setLoginOpen(false), []);

  if (!hotel.has_phone && !hotel.has_whatsapp && !hotel.has_telegram) return null;

  const load = async () => {
    setState('loading');
    try {
      setContact(await apiGet<HotelContact>(`/api/hotels/${hotel.id}/contact`));
      setState('done');
      haptic('success');
    } catch (error) {
      if (error instanceof ApiError && error.isUnauthorized) {
        setState('login');
        setLoginOpen(true);
        return;
      }
      setState('error');
      haptic('error');
    }
  };

  // Гость (и ответ 401): контакты только после входа
  const needLogin = state === 'login' || (!user && !authLoading);
  const busy = state === 'loading';
  const phone = contact.phone?.trim() ?? '';

  /** Кнопка до загрузки контактов: любая из них запрашивает все контакты разом */
  const loader = (label: string, icon: ReactNode, className: string) => (
    <button
      type="button"
      className={className}
      disabled={busy}
      aria-busy={busy}
      onClick={() => void load()}
    >
      {busy ? <span className="spinner" aria-hidden="true" /> : icon}
      {label}
    </button>
  );

  return (
    <section className="hotel-contacts flex min-w-0 flex-col gap-3" aria-label={ht.contacts}>
      {needLogin ? (
        <button
          type="button"
          className={SECONDARY_CLASS}
          aria-haspopup="dialog"
          onClick={() => {
            haptic('light');
            setLoginOpen(true);
          }}
        >
          <Icon name="lock" className="size-4" />
          {ht.contact_login}
        </button>
      ) : state === 'done' ? (
        <>
          {phone && (
            <a href={`tel:${phone.replace(/\s/g, '')}`} className={PRIMARY_CLASS}>
              <Icon name="phone" className="size-4" />
              <span dir="ltr">{phone}</span>
            </a>
          )}
          {contact.whatsapp_url && (
            <ExternalLink href={contact.whatsapp_url} className={SECONDARY_CLASS}>
              <Icon name="message" className="size-4" />
              WhatsApp
            </ExternalLink>
          )}
          {contact.telegram_url && (
            <ExternalLink href={contact.telegram_url} className={SECONDARY_CLASS}>
              <TelegramIcon />
              Telegram
            </ExternalLink>
          )}
        </>
      ) : (
        <>
          {hotel.has_phone &&
            loader(ht.call, <Icon name="phone" className="size-4" />, PRIMARY_CLASS)}
          {hotel.has_whatsapp &&
            loader('WhatsApp', <Icon name="message" className="size-4" />, SECONDARY_CLASS)}
          {hotel.has_telegram && loader('Telegram', <TelegramIcon />, SECONDARY_CLASS)}
        </>
      )}

      {state === 'error' && (
        <p className="m-0 text-center text-xs font-medium text-[var(--danger)]" role="alert">
          {ht.contact_error}
        </p>
      )}

      <Modal open={loginOpen} title={ht.contacts} onClose={closeLogin}>
        <OpenInTelegram plain />
      </Modal>
    </section>
  );
}
