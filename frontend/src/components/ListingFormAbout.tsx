import { FEATURE_CODES, featureName } from '../i18n/features';
import { fillVars } from '../lib/format';
import { LISTING_DESCRIPTION_MAX, LISTING_DESCRIPTION_MIN } from '../lib/ownerListings';
import { useI18n } from '../providers/I18nProvider';
import { FORM_LEGEND_CLASS } from './HotelFormMain';
import type { ListingFormStepProps } from './ListingFormPlace';
import PillGroup from './PillGroup';
import TextAreaField from './TextAreaField';

/** Шаг 3 размещения: описание на любом языке (переводит AI) и удобства */
export default function ListingFormAbout({ draft, onChange }: ListingFormStepProps) {
  const { lang, t } = useI18n();

  const toggleFeature = (code: string) => {
    const next = draft.features.includes(code)
      ? draft.features.filter((item) => item !== code)
      : [...draft.features, code];
    onChange({ features: next });
  };

  return (
    <>
      <TextAreaField
        label={t.listing.description}
        name="description"
        rows={8}
        maxLength={LISTING_DESCRIPTION_MAX}
        hint={fillVars(t.listing_form.description_hint, { n: LISTING_DESCRIPTION_MIN })}
        value={draft.description}
        onChange={(event) => onChange({ description: event.target.value })}
      />
      <PillGroup
        legend={t.filters.features}
        legendClassName={FORM_LEGEND_CLASS}
        options={FEATURE_CODES.map((code) => ({
          value: code as string,
          label: featureName(code, lang) ?? code,
        }))}
        selected={draft.features}
        onToggle={toggleFeature}
      />
    </>
  );
}
