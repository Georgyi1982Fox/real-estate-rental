import { fill, formatPrice } from '../lib/format';
import { DAILY_PRICE_STEP, PRICE_MAX, PRICE_STEP } from '../lib/searchFilters';
import { useI18n } from '../providers/I18nProvider';
import RangeField from './RangeField';

const NAMES = { min: 'min_price', max: 'max_price' };

interface PriceRangeProps {
  min?: number;
  max?: number;
  /** Вызывается только с корректной парой (min ≤ max ≤ PRICE_MAX) */
  onChange: (min: number | undefined, max: number | undefined) => void;
  inputClassName: string;
  /** Подпись «Цена»: по умолчанию мелкая, в окне фильтров — как заголовки остальных полей */
  labelClassName?: string;
  /** Посуточная аренда: цена за сутки, шаг мельче */
  daily?: boolean;
}

/** Цена «от — до»: RangeField с подписями и пределом цены */
export default function PriceRange({ daily, ...props }: PriceRangeProps) {
  const { t } = useI18n();
  const ht = t.home;

  return (
    <RangeField
      {...props}
      label={daily ? ht.price_daily : ht.price}
      minLabel={ht.price_min}
      maxLabel={ht.price_max}
      names={NAMES}
      limit={PRICE_MAX}
      step={daily ? DAILY_PRICE_STEP : PRICE_STEP}
      errors={{
        min: ht.price_min_error,
        max: ht.price_max_error,
        limit: fill(ht.price_limit_error, formatPrice(PRICE_MAX)),
      }}
    />
  );
}
