import type { MyHotel } from '../api/types';
import { fill } from '../lib/format';
import { HOTEL_PHOTO_MAX_BYTES, HOTEL_PHOTOS_MAX, hotelErrorTexts } from '../lib/hotelForm';
import { useI18n } from '../providers/I18nProvider';
import PhotoUploader from './PhotoUploader';

interface HotelPhotosProps {
  hotel: MyHotel;
  /** Сервер после каждого фото отдаёт объект целиком */
  onChange: (hotel: MyHotel) => void;
}

/** Шаг 7 формы размещения: фото объекта, до 20 штук */
export default function HotelPhotos({ hotel, onChange }: HotelPhotosProps) {
  const { t } = useI18n();
  const ft = t.hotel_form;

  return (
    <PhotoUploader<MyHotel>
      images={hotel.images ?? []}
      path={`/api/my/hotels/${hotel.id}/photos`}
      max={HOTEL_PHOTOS_MAX}
      maxBytes={HOTEL_PHOTO_MAX_BYTES}
      onChange={onChange}
      errorText={(error) => hotelErrorTexts(error, ft, 0)[0] ?? ft.errors.generic}
      label={ft.steps.photos}
      hint={fill(ft.photos_hint, HOTEL_PHOTOS_MAX)}
      addLabel={ft.add_photo}
      uploadingLabel={ft.uploading}
      deleteLabel={ft.photo_delete}
      tooManyText={ft.errors.too_many_photos}
      tooBigText={ft.errors.bad_photo}
    />
  );
}
