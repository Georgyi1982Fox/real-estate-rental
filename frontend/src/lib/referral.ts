// «Пригласи друга» (FRONTEND-029, бэкенд — TASK-108)

/** Страница приглашения: ссылка, условия, счётчики */
export const INVITE_PATH = '/invite';

export const REFERRAL_API = '/api/referral';
export const REFERRAL_APPLY_API = '/api/referral/apply';

/** Параметр запуска по ссылке друга: startapp=ref_<код> */
const START_PREFIX = 'ref_';
/** Бэкенд принимает код не длиннее 40 символов */
const CODE_MAX = 40;

/** Код приглашения из параметра запуска; null — мини-апп открыли не по ссылке друга */
export function referralStartCode(startParam: string): string | null {
  const value = startParam.trim();
  if (!value.startsWith(START_PREFIX) || value.length <= START_PREFIX.length) return null;
  return value.length <= CODE_MAX ? value : null;
}
