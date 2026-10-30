import type { MyListing } from '../api/types';
import { fill } from '../lib/format';
import {
  DEFAULT_LISTINGS_LIMIT,
  LISTING_PHOTO_MAX_BYTES,
  LISTING_PHOTOS_MAX,
  listingErrorText,
} from '../lib/ownerListings';
import { useI18n } from '../providers/I18nProvider';
import PhotoUploader from './PhotoUploader';

interface ListingPhotosProps {
  listing: MyListing;
  /** Сервер после каждого фото отдаёт объявление целиком */
  onChange: (listing: MyListing) => void;
}

/** Фото своего объявления: последний шаг размещения и окно «Фото» в «Моих объявлениях» */
export default function ListingPhotos({ listing, onChange }: ListingPhotosProps) {
  const { t } = useI18n();
  const ft = t.listing_form;

  return (
    <PhotoUploader<MyListing>
      images={listing.images ?? []}
      path={`/api/my/listings/${listing.id}/photos`}
      max={LISTING_PHOTOS_MAX}
      maxBytes={LISTING_PHOTO_MAX_BYTES}
      onChange={onChange}
      errorText={(error) => listingErrorText(error, ft, DEFAULT_LISTINGS_LIMIT)}
      label={ft.steps.photos}
      hint={fill(t.hotel_form.photos_hint, LISTING_PHOTOS_MAX)}
      addLabel={t.hotel_form.add_photo}
      uploadingLabel={ft.uploading}
      deleteLabel={t.hotel_form.photo_delete}
      tooManyText={ft.errors.too_many_photos}
      tooBigText={ft.errors.photo_size}
    />
  );
}
