import type { Currency, RentPeriod } from '../api/types';
import {
  CURRENCY_LABELS,
  LISTING_CURRENCIES,
  LISTING_PRICE_MAX,
  LISTING_ROOMS,
} from '../lib/ownerListings';
import { useI18n } from '../providers/I18nProvider';
import FormField from './FormField';
import { FORM_LEGEND_CLASS } from './HotelFormMain';
import type { ListingFormStepProps } from './ListingFormPlace';
import PillGroup from './PillGroup';
import SelectField from './SelectField';

const ROOMS_TOP = LISTING_ROOMS[LISTING_ROOMS.length - 1];

/** Шаг 2 размещения: помесячно / посуточно, комнаты, площадь, цена, этаж */
export default function ListingFormFlat({ draft, onChange }: ListingFormStepProps) {
  const { t } = useI18n();
  const ft = t.listing_form;
  const periods: { value: RentPeriod; label: string }[] = [
    { value: 'monthly', label: t.filters.monthly },
    { value: 'daily', label: t.filters.daily },
  ];
  const rooms = LISTING_ROOMS.map((value) => ({
    value,
    label: value === 1 ? ft.room_studio : value === ROOMS_TOP ? `${value}+` : String(value),
  }));

  return (
    <>
      <PillGroup
        legend={t.filters.rent_period}
        legendClassName={FORM_LEGEND_CLASS}
        options={periods}
        selected={[draft.rent_period]}
        onToggle={(rent_period) => onChange({ rent_period })}
      />
      <PillGroup<number>
        legend={ft.rooms}
        legendClassName={FORM_LEGEND_CLASS}
        options={rooms}
        selected={draft.rooms === null ? [] : [draft.rooms]}
        onToggle={(value) => onChange({ rooms: value })}
        compact
      />
      <FormField
        label={ft.area}
        name="area"
        type="number"
        inputMode="decimal"
        min={10}
        max={1000}
        step="any"
        value={draft.area}
        onChange={(event) => onChange({ area: event.target.value })}
      />
      <div className="grid grid-cols-2 gap-3">
        <FormField
          label={draft.rent_period === 'daily' ? ft.price_day : ft.price_month}
          name="price"
          type="number"
          inputMode="decimal"
          min={1}
          max={LISTING_PRICE_MAX}
          step="any"
          value={draft.price}
          onChange={(event) => onChange({ price: event.target.value })}
        />
        <SelectField
          label={t.hotel_form.room_currency}
          name="currency"
          value={draft.currency}
          options={LISTING_CURRENCIES.map((code) => ({
            value: code,
            label: CURRENCY_LABELS[code] ?? code,
          }))}
          onChange={(currency) => onChange({ currency: currency as Currency })}
        />
        <FormField
          label={ft.floor}
          name="floor"
          type="number"
          inputMode="numeric"
          min={0}
          max={60}
          value={draft.floor}
          onChange={(event) => onChange({ floor: event.target.value })}
        />
        <FormField
          label={ft.total_floors}
          name="total_floors"
          type="number"
          inputMode="numeric"
          min={1}
          max={60}
          value={draft.total_floors}
          onChange={(event) => onChange({ total_floors: event.target.value })}
        />
      </div>
    </>
  );
}
