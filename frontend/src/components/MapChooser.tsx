import { mapLinks } from '../lib/maps';
import type { MapTarget } from '../lib/maps';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';
import { useToast } from '../providers/ToastProvider';
import ExternalLink from './ExternalLink';
import Icon from './Icon';
import Modal from './Modal';

interface MapChooserProps {
  open: boolean;
  onClose: () => void;
  target: MapTarget;
  /** Адрес, который видит человек (и копирует) */
  place: string;
}

const OPTION_CLASS =
  'map-chooser__option flex min-h-16 w-full items-center gap-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-left hover:bg-[var(--surface-hover)] active:scale-[.98]';

/** Знак сервиса — цветной кружок с буквой (логотипы брендов не тянем) */
function Mark({ letter, className }: { letter: string; className: string }) {
  return (
    <span
      className={`inline-grid size-10 shrink-0 place-items-center rounded-full text-base font-bold text-white ${className}`}
      aria-hidden="true"
    >
      {letter}
    </span>
  );
}

/** «Открыть в картах»: выбор Google Maps или Яндекс Карт, ниже — скопировать адрес */
export default function MapChooser({ open, onClose, target, place }: MapChooserProps) {
  const { t } = useI18n();
  const mt = t.listing.map;
  const showToast = useToast();
  const links = mapLinks(target);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(place);
      haptic('success');
      showToast(mt.copied, 'success');
    } catch {
      haptic('error');
    }
    onClose();
  };

  return (
    <Modal open={open} title={mt.open} onClose={onClose}>
      <div className="map-chooser flex flex-col gap-3">
        {place && (
          <p className="m-0 flex items-start gap-2 text-sm text-[var(--text-secondary)]">
            <Icon name="pin" className="mt-0.5 size-4 shrink-0" />
            {place}
          </p>
        )}
        {links && (
          <>
            <ExternalLink href={links.google} className={OPTION_CLASS}>
              <Mark letter="G" className="bg-[var(--brand-google-blue)]" />
              <span className="min-w-0 flex-1 text-sm font-semibold">{mt.google}</span>
              <Icon name="external" className="size-4 text-[var(--text-secondary)]" />
            </ExternalLink>
            <ExternalLink href={links.yandex} className={OPTION_CLASS}>
              <Mark letter={mt.yandex_letter} className="bg-[var(--brand-yandex)]" />
              <span className="min-w-0 flex-1 text-sm font-semibold">{mt.yandex}</span>
              <Icon name="external" className="size-4 text-[var(--text-secondary)]" />
            </ExternalLink>
          </>
        )}
        {place && (
          <button
            type="button"
            className="map-chooser__copy inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-md)] px-4 text-sm font-semibold text-[var(--text-primary)] hover:bg-[var(--surface-hover)]"
            onClick={() => void copy()}
          >
            <Icon name="copy" className="size-4" />
            {mt.copy}
          </button>
        )}
      </div>
    </Modal>
  );
}
