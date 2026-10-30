import { useState } from 'react';
import type { FormEvent } from 'react';
import type { ListingId, MyListing } from '../api/types';
import {
  CURRENCY_LABELS,
  LISTING_CURRENCIES,
  LISTING_PRICE_MAX,
  isListingPrice,
} from '../lib/ownerListings';
import { useI18n } from '../providers/I18nProvider';
import { DIALOG_BUTTON_CLASS, DIALOG_CANCEL_CLASS } from './ConfirmDialog';
import FormField from './FormField';
import Modal from './Modal';
import SelectField from './SelectField';

interface ListingPriceModalProps {
  /** Объявление, цену которого меняют; null — окно закрыто */
  listing: MyListing | null;
  busy: boolean;
  onSubmit: (price: number, currency: string) => void;
  onClose: () => void;
}

/** «Изменить цену»: новая цена и валюта. Снижение уходит в уведомления «цена снижена» */
export default function ListingPriceModal({
  listing,
  busy,
  onSubmit,
  onClose,
}: ListingPriceModalProps) {
  const { t } = useI18n();
  const ft = t.listing_form;
  const [shownId, setShownId] = useState<ListingId | null>(null);
  const [price, setPrice] = useState('');
  const [currency, setCurrency] = useState('GEL');
  const [invalid, setInvalid] = useState(false);

  // Каждое открытие — с текущей цены объявления
  const id = listing?.id ?? null;
  if (id !== shownId) {
    setShownId(id);
    if (listing) {
      setPrice(String(listing.price));
      setCurrency(listing.currency);
      setInvalid(false);
    }
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    const value = Number(price);
    if (price === '' || !isListingPrice(value)) {
      setInvalid(true);
      return;
    }
    onSubmit(value, currency);
  };

  return (
    <Modal open={listing !== null} title={t.my_listings.price_title} onClose={onClose}>
      <form className="listing-price-form flex flex-col gap-4" noValidate onSubmit={handleSubmit}>
        <div className="grid grid-cols-2 gap-3">
          <FormField
            label={listing?.rent_period === 'daily' ? ft.price_day : ft.price_month}
            name="price"
            type="number"
            inputMode="decimal"
            min={1}
            max={LISTING_PRICE_MAX}
            step="any"
            required
            error={invalid ? ft.need_price : undefined}
            value={price}
            onChange={(event) => {
              setInvalid(false);
              setPrice(event.target.value);
            }}
          />
          <SelectField
            label={t.hotel_form.room_currency}
            name="currency"
            value={currency}
            options={LISTING_CURRENCIES.map((code) => ({
              value: code,
              label: CURRENCY_LABELS[code] ?? code,
            }))}
            onChange={setCurrency}
          />
        </div>
        <footer className="listing-price-form__actions mt-2 flex gap-3">
          <button type="button" className={DIALOG_CANCEL_CLASS} onClick={onClose}>
            {t.common.cancel}
          </button>
          <button
            type="submit"
            className={`${DIALOG_BUTTON_CLASS} bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)]`}
            disabled={busy}
            aria-busy={busy}
          >
            {t.hotel_form.save}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
