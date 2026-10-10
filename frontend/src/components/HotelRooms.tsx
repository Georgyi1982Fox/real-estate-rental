import type { HotelRoom } from '../api/types';
import { roomKindName } from '../i18n/hotels';
import { formatPrice, plural } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';
import Icon from './Icon';

interface HotelRoomsProps {
  rooms: HotelRoom[];
}

const CELL_CLASS = 'px-2 py-3 align-top first:pl-0 last:pr-0';
const HEAD_CLASS = `${CELL_CLASS} text-xs font-medium text-[var(--text-secondary)]`;

/** Таблица номеров: тип (и своё название), гостей, цена за ночь, «N номеров». Нет номеров — блока нет */
export default function HotelRooms({ rooms }: HotelRoomsProps) {
  const { lang, t } = useI18n();
  const ht = t.hotels;

  if (rooms.length === 0) return null;

  return (
    <section
      className="hotel-rooms space-y-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5"
      aria-labelledby="hotel-rooms-title"
    >
      <h2 id="hotel-rooms-title" className="text-lg font-semibold">
        {ht.rooms}
      </h2>
      <table className="hotel-rooms__table w-full border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-[var(--border)]">
            <th scope="col" className={HEAD_CLASS}>
              {ht.room}
            </th>
            <th scope="col" className={HEAD_CLASS}>
              {ht.room_guests}
            </th>
            <th scope="col" className={`${HEAD_CLASS} text-right`}>
              {ht.room_price}
            </th>
          </tr>
        </thead>
        <tbody>
          {rooms.map((room) => {
            const kind = roomKindName(room.kind, lang);
            const title = room.title?.trim() || kind || room.kind;
            return (
              <tr key={room.id} className="border-b border-[var(--border)] last:border-b-0">
                <th scope="row" className={`${CELL_CLASS} min-w-0 font-normal`}>
                  <span className="block break-words font-semibold text-[var(--text-primary)]">
                    {title}
                  </span>
                  <span className="block text-xs text-[var(--text-secondary)]">
                    {/* Тип — если у номера своё название */}
                    {kind && kind !== title && `${kind} · `}
                    {plural(ht.rooms_count, room.count, lang)}
                  </span>
                </th>
                <td className={`${CELL_CLASS} whitespace-nowrap`}>
                  <span className="inline-flex items-center gap-1.5">
                    <Icon name="users" className="size-4 text-[var(--text-secondary)]" />
                    {room.guests}
                  </span>
                </td>
                <td className={`${CELL_CLASS} whitespace-nowrap text-right font-semibold`}>
                  {formatPrice(room.price, room.currency)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
