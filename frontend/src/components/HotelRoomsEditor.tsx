import { useCallback, useState } from 'react';
import type { HotelRoomInput } from '../api/types';
import { roomKindName } from '../i18n/hotels';
import { fill, formatMoney, plural } from '../lib/format';
import { HOTEL_ROOMS_MAX } from '../lib/hotelForm';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import HotelRoomModal from './HotelRoomModal';
import Icon from './Icon';

interface HotelRoomsEditorProps {
  rooms: HotelRoomInput[];
  /** Сохранить номер: index — какой правили, null — новый. false — не сохранилось, окно остаётся */
  onSave: (room: HotelRoomInput, index: number | null) => Promise<boolean>;
  onRemove: (index: number) => Promise<boolean>;
}

/** Шаг 5 формы размещения: список номеров с добавлением, правкой и удалением */
export default function HotelRoomsEditor({ rooms, onSave, onRemove }: HotelRoomsEditorProps) {
  const { lang, t } = useI18n();
  const ft = t.hotel_form;
  // Какой номер открыт в окне: индекс, 'new' или null — окно закрыто
  const [editing, setEditing] = useState<number | 'new' | null>(null);
  const [busy, setBusy] = useState(false);
  // Стабильная ссылка: Modal перезапускает эффект (фокус) при смене onClose
  const close = useCallback(() => setEditing(null), []);

  const save = async (room: HotelRoomInput) => {
    setBusy(true);
    const saved = await onSave(room, typeof editing === 'number' ? editing : null);
    setBusy(false);
    if (saved) setEditing(null);
  };

  const remove = async (index: number) => {
    haptic('light');
    setBusy(true);
    await onRemove(index);
    setBusy(false);
  };

  return (
    <section className="hotel-rooms-editor flex flex-col gap-3" aria-label={t.hotels.rooms}>
      {rooms.length === 0 ? (
        <p className="m-0 rounded-[var(--radius-md)] border border-dashed border-[var(--border)] px-4 py-6 text-center text-sm text-[var(--text-secondary)]">
          {ft.rooms_empty}
        </p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {rooms.map((room, index) => {
            const kind = roomKindName(room.kind, lang) ?? room.kind;
            const title = room.title.trim() || kind;
            return (
              // Номера без своего ID (до размещения) различаются только местом в списке
              <li
                key={index}
                className="hotel-rooms-editor__room flex min-w-0 items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] py-2 pl-4 pr-2"
              >
                <p className="m-0 min-w-0 flex-1 text-sm">
                  <span className="block break-words font-semibold">{title}</span>
                  <span className="block text-xs text-[var(--text-secondary)]">
                    {title !== kind && `${kind} · `}
                    {fill(t.hotels.guests_chip, room.guests)} ·{' '}
                    {plural(t.hotels.rooms_count, room.count, lang)}
                  </span>
                </p>
                <span className="shrink-0 whitespace-nowrap text-sm font-semibold">
                  {formatMoney(room.price, room.currency)}
                </span>
                <button
                  type="button"
                  className="app-icon-button shrink-0"
                  aria-label={`${ft.edit_room}: ${title}`}
                  aria-haspopup="dialog"
                  disabled={busy}
                  onClick={() => {
                    haptic('light');
                    setEditing(index);
                  }}
                >
                  <Icon name="pencil" className="size-4" />
                </button>
                <button
                  type="button"
                  className="app-icon-button shrink-0"
                  aria-label={`${t.my_hotels.delete}: ${title}`}
                  disabled={busy}
                  onClick={() => void remove(index)}
                >
                  <Icon name="trash" className="size-4" />
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {rooms.length < HOTEL_ROOMS_MAX && (
        <button
          type="button"
          className="inline-flex min-h-11 items-center justify-center gap-2 self-start rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-2.5 text-sm font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-hover)] active:scale-[.98]"
          aria-haspopup="dialog"
          onClick={() => {
            haptic('light');
            setEditing('new');
          }}
        >
          <Icon name="plus" className="size-4" />
          {ft.add_room}
        </button>
      )}

      <HotelRoomModal
        open={editing !== null}
        room={typeof editing === 'number' ? (rooms[editing] ?? null) : null}
        busy={busy}
        onSubmit={(room) => void save(room)}
        onClose={close}
      />
    </section>
  );
}
