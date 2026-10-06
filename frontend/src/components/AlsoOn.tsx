import { Fragment } from 'react';
import type { SiteLink } from '../lib/sources';
import { useI18n } from '../providers/I18nProvider';
import ExternalLink from './ExternalLink';

interface AlsoOnProps {
  links: SiteLink[];
}

/** «Также на: MyHome.ge, Livo.ge» — та же квартира на других сайтах */
export default function AlsoOn({ links }: AlsoOnProps) {
  const { t } = useI18n();

  if (links.length === 0) return null;

  return (
    <p className="also-on m-0 break-words text-sm text-[var(--text-secondary)]">
      {t.listing.also_on}{' '}
      {links.map((link, index) => (
        <Fragment key={link.url}>
          {index > 0 && ', '}
          <ExternalLink
            href={link.url}
            className="also-on__link whitespace-nowrap font-semibold text-[var(--primary)] underline-offset-2 hover:underline"
          >
            {link.name} ↗
          </ExternalLink>
        </Fragment>
      ))}
    </p>
  );
}
