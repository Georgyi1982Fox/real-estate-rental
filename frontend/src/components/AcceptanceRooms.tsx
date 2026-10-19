import { useCallback, useEffect, useRef, useState } from 'react';
import type { AcceptanceChecklist, AcceptanceRoomType } from '../api/types';
import {
  addRoom,
  markRoomOk,
  orderedRooms,
  removeRoom,
  roomCount,
  roomItemCode,
  roomKey,
  roomMarked,
  roomTitle,
  toggleMark,
} from '../lib/acceptance';
import type { AcceptanceDraft, AcceptanceRoom } from '../lib/acceptance';
import { fill, fillVars } from '../lib/format';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import AcceptanceItemRow from './AcceptanceItemRow';
import ConfirmDialog from './ConfirmDialog';
import Icon from './Icon';
import type { IconName } from './Icon';

/** Иконка и цвет (--tone-* из theme.css) типа комнаты; незнакомый тип — домик */
const ROOM_LOOK: Record<string, { icon: IconName; tone: string }> = {
  hallway: { icon: 'door', tone: 'bg-[var(--tone-more)]' },
  living_room: { icon: 'sofa', tone: 'bg-[var(--tone-hero)]' },
  bedroom: { icon: 'bed', tone: 'bg-[var(--tone-housing)]' },
  kitchen: { icon: 'utensils', tone: 'bg-[var(--tone-benefit)]' },
  bathroom: { icon: 'droplet', tone: 'bg-[var(--tone-owner)]' },
  balcony: { icon: 'balcony', tone: 'bg-[var(--tone-search)]' },
  whole: { icon: 'home', tone: 'bg-[var(--primary)]' },
};
const DEFAULT_LOOK = { icon: 'home' as IconName, tone: 'bg-[var(--tone-more)]' };

function look(type: string) {
  return ROOM_LOOK[type] ?? DEFAULT_LOOK;
}

/** Цветной значок комнаты; shape — размер и скругление */
function RoomIcon({ type, shape = 'size-11 rounded-xl' }: { type: string; shape?: string }) {
  const { icon, tone } = look(type);
  return (
    <span
      className={`acceptance-room__icon inline-grid ${shape} shrink-0 place-items-center text-[var(--surface)] shadow-[var(--shadow-sm)] ${tone}`}
    >
      <Icon name={icon} className="size-[55%]" />
    </span>
  );
}

interface RoomCardProps {
  room: AcceptanceRoom;
  type: AcceptanceRoomType;
  title: string;
  statuses: AcceptanceChecklist['statuses'];
  draft: AcceptanceDraft;
  expanded: boolean;
  onToggle: () => void;
  onRemove: () => void;
  onChange: (patch: Partial<AcceptanceDraft>) => void;
}

/** Комната: заголовок с прогрессом (нажатие сворачивает), внутри — пункты, «Всё в порядке», «Удалить» */
function RoomCard({
  room,
  type,
  title,
  statuses,
  draft,
  expanded,
  onToggle,
  onRemove,
  onChange,
}: RoomCardProps) {
  const { t } = useI18n();
  const at = t.acceptance;
  const marked = roomMarked(draft, room, type);
  const total = type.items.length;
  const complete = marked === total;
  const bodyId = `acceptance-room-${roomKey(room)}`;

  return (
    <section
      className={`acceptance-room overflow-hidden rounded-[var(--radius-lg)] border bg-[var(--surface)] shadow-[var(--shadow-sm)] transition-colors ${
        complete ? 'border-[var(--success-text)]/40' : 'border-[var(--border)]'
      }`}
    >
      <button
        type="button"
        className="acceptance-room__header flex w-full items-center gap-3 p-4 text-left hover:bg-[var(--surface-hover)]"
        aria-expanded={expanded}
        aria-controls={bodyId}
        aria-label={fill(expanded ? at.collapse_room : at.expand_room, title)}
        onClick={() => {
          haptic('selection');
          onToggle();
        }}
      >
        <RoomIcon type={room.type} />
        <span className="flex min-w-0 flex-1 flex-col gap-1.5">
          <span className="flex items-center gap-2">
            <span className="acceptance-room__title truncate text-base font-semibold">{title}</span>
            {complete && (
              <span className="inline-flex items-center gap-1 rounded-full bg-[var(--success-bg)] px-2 py-0.5 text-xs font-semibold text-[var(--success-text)]">
                <Icon name="check" className="size-3" />
                {at.room_done}
              </span>
            )}
          </span>
          {/* Прогресс комнаты: полоса и «Отмечено 3 из 10» */}
          <span
            className="acceptance-room__bar block h-1.5 w-full overflow-hidden rounded-full bg-[var(--surface-hover)]"
            aria-hidden="true"
          >
            <span
              className="block h-full rounded-full bg-[var(--primary)] transition-[width] duration-300"
              style={{ width: `${total ? (marked / total) * 100 : 0}%` }}
            />
          </span>
          <span className="text-xs text-[var(--text-secondary)] tabular-nums">
            {fillVars(at.room_progress, { n: marked, total })}
          </span>
        </span>
        <Icon
          name="chevron_down"
          className={`size-5 shrink-0 text-[var(--text-secondary)] transition-transform duration-200 ${
            expanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {expanded && (
        <div id={bodyId} className="acceptance-room__body border-t border-[var(--border)] px-4 pb-1">
          <div className="acceptance-room__actions flex items-center gap-2 pt-3">
            <button
              type="button"
              className="inline-flex min-h-10 items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3.5 py-2 text-sm font-medium whitespace-nowrap hover:bg-[var(--surface-hover)] active:scale-[.97] disabled:opacity-60"
              disabled={complete}
              onClick={() => {
                haptic('light');
                onChange({ items: markRoomOk(draft, room, type) });
              }}
            >
              <Icon name="check" className="size-4 text-[var(--success-text)]" />
              {at.all_ok}
            </button>
            <button
              type="button"
              className="ml-auto inline-flex min-h-10 items-center gap-1.5 rounded-full px-3 py-2 text-sm font-medium whitespace-nowrap text-[var(--danger)] hover:bg-[var(--danger-bg)] active:scale-[.97]"
              aria-label={`${at.remove_room}: ${title}`}
              onClick={onRemove}
            >
              <Icon name="trash" className="size-4" />
              {at.remove_short}
            </button>
          </div>
          <ul className="acceptance-room__items m-0 mt-1 list-none divide-y divide-[var(--border)] p-0">
            {type.items.map((item) => {
              const code = roomItemCode(room, item.code);
              return (
                <AcceptanceItemRow
                  key={code}
                  item={item}
                  statuses={statuses}
                  mark={draft.items[code]}
                  onStatus={(status) => onChange({ items: toggleMark(draft, code, status) })}
                  onComment={(comment) => {
                    const mark = draft.items[code];
                    if (mark) onChange({ items: { ...draft.items, [code]: { ...mark, comment } } });
                  }}
                />
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}

interface AcceptanceRoomsProps {
  checklist: AcceptanceChecklist;
  draft: AcceptanceDraft;
  onChange: (patch: Partial<AcceptanceDraft>) => void;
}

/**
 * Чек-лист по комнатам: сначала пусто — человек добавляет комнаты, которые есть в квартире
 * (несколько спален, две ванные…). Добавленная комната раскрывается, остальные свёрнуты
 */
export default function AcceptanceRooms({ checklist, draft, onChange }: AcceptanceRoomsProps) {
  const { t } = useI18n();
  const at = t.acceptance;
  const rooms = orderedRooms(draft, checklist);
  // Раскрытые комнаты; при открытии акта — только первая неготовая, чтобы список был коротким
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(() => {
    const first = rooms.find(({ room, type }) => roomMarked(draft, room, type) < type.items.length);
    return new Set(first ? [roomKey(first.room)] : []);
  });
  const [removing, setRemoving] = useState<AcceptanceRoom | null>(null);
  const closeRemove = useCallback(() => setRemoving(null), []);
  // Только что добавленная комната: прокрутить к ней
  const [added, setAdded] = useState<string | null>(null);
  const cardRefs = useRef(new Map<string, HTMLLIElement>());

  useEffect(() => {
    if (!added) return;
    cardRefs.current.get(added)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    setAdded(null);
  }, [added]);

  const add = (type: AcceptanceRoomType) => {
    const room = addRoom(draft, type);
    if (!room) return;
    haptic('light');
    onChange({ rooms: [...draft.rooms, room] });
    const key = roomKey(room);
    // Новая комната раскрыта, остальные сворачиваются — на экране одна комната
    setExpanded(new Set([key]));
    setAdded(key);
  };

  const toggle = (key: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const remove = (room: AcceptanceRoom) => {
    haptic('medium');
    onChange(removeRoom(draft, room));
    setRemoving(null);
  };

  const removingTitle = removing
    ? rooms.find(({ room }) => roomKey(room) === roomKey(removing))
    : undefined;

  return (
    <div className="acceptance-rooms flex flex-col gap-3">
      {rooms.length === 0 ? (
        <div className="acceptance-rooms__empty flex flex-col items-center gap-2 rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] bg-[var(--surface)] px-6 py-7 text-center">
          <span className="inline-grid size-14 place-items-center rounded-2xl bg-[var(--primary)]/15 text-[var(--primary)]">
            <Icon name="list_checks" className="size-7" />
          </span>
          <p className="m-0 text-base font-semibold">{at.rooms_empty_title}</p>
          <p className="m-0 max-w-sm text-sm leading-relaxed text-[var(--text-secondary)]">
            {at.rooms_empty_text}
          </p>
        </div>
      ) : (
        <ul className="acceptance-rooms__list m-0 flex list-none flex-col gap-3 p-0">
          {rooms.map(({ room, type }) => {
            const key = roomKey(room);
            return (
              <li
                key={key}
                ref={(element) => {
                  if (element) cardRefs.current.set(key, element);
                  else cardRefs.current.delete(key);
                }}
                className="scroll-mt-20"
              >
                <RoomCard
                  room={room}
                  type={type}
                  title={roomTitle(room, type, draft)}
                  statuses={checklist.statuses}
                  draft={draft}
                  expanded={expanded.has(key)}
                  onToggle={() => toggle(key)}
                  onRemove={() => {
                    // Без отметок — сразу, с отметками — спросить
                    if (roomMarked(draft, room, type) === 0) remove(room);
                    else setRemoving(room);
                  }}
                  onChange={onChange}
                />
              </li>
            );
          })}
        </ul>
      )}

      <section className="acceptance-rooms__add flex flex-col gap-2" aria-label={at.add_room}>
        <h3 className="m-0 px-1 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          {at.add_room}
        </h3>
        {/* Типы комнат «таблетками»: «+ Спальня», рядом — сколько уже добавлено */}
        <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
          {checklist.rooms.map((type) => {
            const count = roomCount(draft, type.code);
            const full = count >= type.max_count;
            return (
              <li key={type.code} className="min-w-0">
                <button
                  type="button"
                  className="acceptance-rooms__type inline-flex min-h-11 items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] py-1.5 pr-3.5 pl-1.5 text-sm font-medium shadow-[var(--shadow-sm)] hover:bg-[var(--surface-hover)] active:scale-[.97] disabled:opacity-50"
                  disabled={full}
                  aria-label={`${at.add_room}: ${type.title}${full ? ` (${at.room_full})` : ''}`}
                  onClick={() => add(type)}
                >
                  <RoomIcon type={type.code} shape="size-8 rounded-full" />
                  <span className="whitespace-nowrap">{type.title}</span>
                  {count > 0 && (
                    <span className="inline-grid min-w-5 place-items-center rounded-full bg-[var(--primary)] px-1.5 text-[11px] font-semibold text-white tabular-nums">
                      {count}
                    </span>
                  )}
                  {!full && <Icon name="plus" className="size-4 text-[var(--primary)]" />}
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      <ConfirmDialog
        open={removing !== null}
        title={fill(at.remove_room_title, removingTitle ? roomTitle(removingTitle.room, removingTitle.type, draft) : '')}
        text={at.remove_room_text}
        confirmLabel={at.remove_room}
        danger
        onConfirm={() => {
          if (removing) remove(removing);
        }}
        onClose={closeRemove}
      />
    </div>
  );
}
