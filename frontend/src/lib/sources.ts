import type { Listing, ListingSourceLink } from '../api/types';

/** Названия сайтов-источников по коду с бэкенда */
const SITE_NAMES: Record<string, string> = {
  ss: 'SS.ge',
  myhome: 'MyHome.ge',
  livo: 'Livo.ge',
  korter: 'Korter.ge',
  telegram: 'Telegram',
};

/** Код сайта по домену ссылки — когда бэкенд не прислал source или прислал незнакомый */
const HOST_SOURCES: Record<string, string> = {
  'ss.ge': 'ss',
  'myhome.ge': 'myhome',
  'livo.ge': 'livo',
  'korter.ge': 'korter',
  't.me': 'telegram',
  'telegram.me': 'telegram',
};

export interface SiteLink {
  name: string;
  url: string;
}

/** Домен без www./home.: home.ss.ge → ss.ge; не http(s)-ссылка — '' */
function siteHost(url: string): string {
  try {
    const { protocol, hostname } = new URL(url);
    if (protocol !== 'https:' && protocol !== 'http:') return '';
    return hostname.replace(/^(www|home)\./, '');
  } catch {
    return '';
  }
}

/**
 * Название сайта для подписи: по коду источника, иначе по домену ссылки
 * (незнакомый сайт — сам домен). Ссылка битая — '', такую не показываем.
 */
export function siteName(source: string | null | undefined, url: string): string {
  const host = siteHost(url);
  if (!host) return '';
  return SITE_NAMES[source ?? ''] ?? SITE_NAMES[HOST_SOURCES[host] ?? ''] ?? host;
}

/** «Также на»: другие сайты с той же квартирой — без битых ссылок, повторов и самого источника */
export function alsoOnLinks(listing: Pick<Listing, 'also_on' | 'source_url'>): SiteLink[] {
  const seen = new Set<string>(listing.source_url ? [listing.source_url] : []);
  const links: SiteLink[] = [];
  for (const item of listing.also_on ?? []) {
    if (!isSourceLink(item) || seen.has(item.url)) continue;
    const name = siteName(item.source, item.url);
    if (!name) continue;
    seen.add(item.url);
    links.push({ name, url: item.url });
  }
  return links;
}

function isSourceLink(item: ListingSourceLink | null | undefined): item is ListingSourceLink {
  return typeof item?.url === 'string' && item.url !== '';
}
