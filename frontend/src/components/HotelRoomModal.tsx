import { useState } from 'react';
import type { FormEvent } from 'react';
import type { HotelRoomInput } from '../api/types';
import { useHotelOptions } from '../hooks/useHotelOptions';
import { roomKindName } from '../i18n/hotels';
import { ROOM_COUNT_MAX, ROOM_GUESTS_MAX, ROOM_TITLE_MAX, isNightPrice } from '../lib/hotelForm';
import { useI18n } from '../providers/I18nProvider';
import { DIALOG_BUTTON_CLASS, DIALOG_CANCEL_CLASS } from './ConfirmDialog';
import FormField from './FormField';
import Modal from './Modal';
import SelectField from './SelectField';

const DEFAULT_CURRENCIES = ['GEL', 'USD', 'EUR'];
const CURRENCY_LABELS: Record<string, string> = { GEL: '₾ GEL', USD: '$ USD', EUR: '€ EUR' };

interface RoomText {
  kind: string;
  title: string;
  guests: string;
  price: string;
  currency: string;
  count: string;
}

const toText = (room: HotelRoomInput | null): RoomText => ({
  kind: room?.kind ?? '',
  title: room?.title ?? '',
  guests: room ? String(room.guests) : '2',
  price: room ? String(room.price) : '',
  currency: room?.currency ?? 'GEL',
  count: room ? String(room.count) : '1',
});

interface HotelRoomModalProps {
  open: boolean;
  /** Номер, который правят; null — новый */
  room: HotelRoomInput | null;
  busy?: boolean;
  onSubmit: (room: HotelRoomInput) => void;
  onClose: () => void;
}

/** Окно номера: тип, своё название, гостей, цена за ночь и валюта, сколько таких номеров */
export default function HotelRoomModal({
  open,
  room,
  busy = false,
  onSubmit,
  onClose,
}: HotelRoomModalProps) {
  const { lang, t } = useI18n();
  const ft = t.hotel_form;
  const { roomKinds, options } = useHotelOptions();
  const [text, setText] = useState<RoomText>(() => toText(room));
  const [wasOpen, setWasOpen] = useState(open);
  const [priceError, setPriceError] = useState(false);

  // Каждое открытие — с данных номера (или с пустой формы)
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) {
      setText(toText(room));
      setPriceError(false);
    }
  }

  const change = (patch: Partial<RoomText>) => setText((current) => ({ ...current, ...patch }));
  const currencies = options?.currencies.length ? options.currencies : DEFAULT_CURRENCIES;
  const guests = Number(text.guests);
  const price = Number(text.price);
  const count = Number(text.count);
  const ready =
    text.kind !== '' &&
    Number.isInteger(guests) &&
    guests >= 1 &&
    guests <= ROOM_GUESTS_MAX &&
    price > 0 &&
    Number.isInteger(count) &&
    count >= 1 &&
    count <= ROOM_COUNT_MAX;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!ready || busy) return;
    // Та же проверка, что на сервере: ночь от 10 до 5 000 ₾
    if (!isNightPrice(price, text.currency)) {
      setPriceError(true);
      return;
    }
    onSubmit({
      kind: text.kind,
      title: text.title.trim(),
      guests,
      price,
      currency: text.currency,
      count,
    });
  };

  return (
    <Modal open={open} title={room ? ft.edit_room : ft.add_room} onClose={onClose}>
      <form className="hotel-room-form flex flex-col gap-4" onSubmit={handleSubmit}>
        <SelectField
          label={ft.room_kind}
          name="kind"
          value={text.kind}
          placeholder="—"
          options={roomKinds.map((code) => ({
            value: code,
            label: roomKindName(code, lang) ?? code,
          }))}
          onChange={(kind) => change({ kind })}
        />
        <FormField
          label={ft.room_title}
          name="title"
          type="text"
          autoComplete="off"
          maxLength={ROOM_TITLE_MAX}
          value={text.title}
          onChange={(event) => change({ title: event.target.value })}
        />
        <div className="grid grid-cols-2 gap-3">
          <FormField
            label={ft.room_price}
            name="price"
            type="number"
            inputMode="decimal"
            min={1}
            step="any"
            required
            value={text.price}
            onChange={(event) => {
              setPriceError(false);
              change({ price: event.target.value });
            }}
          />
          <SelectField
            label={ft.room_currency}
            name="currency"
            value={text.currency}
            options={currencies.map((code) => ({
              value: code,
              label: CURRENCY_LABELS[code] ?? code,
            }))}
            onChange={(currency) => {
              setPriceError(false);
              change({ currency });
            }}
          />
          <FormField
            label={ft.room_guests}
            name="guests"
            type="number"
            inputMode="numeric"
            min={1}
            max={ROOM_GUESTS_MAX}
            required
            value={text.guests}
            onChange={(event) => change({ guests: event.target.value })}
          />
          <FormField
            label={ft.room_count}
            name="count"
            type="number"
            inputMode="numeric"
            min={1}
            max={ROOM_COUNT_MAX}
            required
            value={text.count}
            onChange={(event) => change({ count: event.target.value })}
          />
        </div>
        {priceError && (
          <p className="m-0 text-sm font-medium text-[var(--danger)]" role="alert">
            {ft.errors.bad_price}
          </p>
        )}
        <footer className="hotel-room-form__actions mt-2 flex gap-3">
          <button type="button" className={DIALOG_CANCEL_CLASS} onClick={onClose}>
            {t.common.cancel}
          </button>
          <button
            type="submit"
            className={`${DIALOG_BUTTON_CLASS} bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)]`}
            disabled={!ready || busy}
            aria-busy={busy}
          >
            {ft.room_save}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
