import { describe, expect, it } from 'vitest';
import type { Listing } from '../api/types';
import { listingPreview, rememberListingPreview } from './listingPreview';

const listing = (id: string) => ({ id, title: `#${id}`, price: 100, currency: 'GEL' }) as Listing;

describe('квартира с карточки списка', () => {
  it('запоминается по ID и находится', () => {
    rememberListingPreview(listing('a1'));
    expect(listingPreview('a1')?.title).toBe('#a1');
    expect(listingPreview('нет такой')).toBeUndefined();
  });

  it('помним 200 последних: самая старая вытесняется', () => {
    rememberListingPreview(listing('first'));
    for (let index = 0; index < 200; index += 1) rememberListingPreview(listing(`n${index}`));
    expect(listingPreview('first')).toBeUndefined();
    expect(listingPreview('n0')).toBeDefined();
    expect(listingPreview('n199')).toBeDefined();
  });

  it('показанная снова становится самой новой', () => {
    for (let index = 0; index < 200; index += 1) rememberListingPreview(listing(`m${index}`));
    rememberListingPreview(listing('m0'));
    rememberListingPreview(listing('extra'));
    expect(listingPreview('m0')).toBeDefined();
    expect(listingPreview('m1')).toBeUndefined();
  });
});
