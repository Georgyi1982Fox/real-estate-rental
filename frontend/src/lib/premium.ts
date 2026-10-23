import type { Plan, SubscriptionLimits } from '../api/types';

// /api/subscription отдаёт лимиты только текущего тарифа, а таблице «Бесплатно / Premium»
// нужны обе колонки: вторую берём отсюда. Эти же значения видит гость (без запроса к API)

// Избранное без ограничений на всех тарифах (TASK-016)
export const FREE_LIMITS: SubscriptionLimits = { favorites: null, searches: 1 };

export const PREMIUM_LIMITS: SubscriptionLimits = { favorites: null, searches: 20 };

/** На бесплатном тарифе уведомление о новой квартире приходит с такой задержкой (TASK-085) */
export const FREE_NOTIFY_DELAY_HOURS = 3;

/** Тарифы для гостя без API — те же, что отдаёт бэкенд (TASK-084) */
export const DEFAULT_PLANS: Plan[] = [
  { id: 'premium_month', tier: 'nomad', days: 30, price_stars: 250 },
  { id: 'premium_week', tier: 'nomad', days: 7, price_stars: 100 },
];

/** Платные тарифы из ответа бэкенда, от короткого к длинному; без ответа — тарифы по умолчанию */
export function premiumPlans(plans: Plan[] | undefined): Plan[] {
  const paid = (plans ?? []).filter((plan) => plan.tier !== 'free' && plan.price_stars > 0);
  return [...(paid.length > 0 ? paid : DEFAULT_PLANS)].sort((a, b) => a.days - b.days);
}

/**
 * Тариф с самой низкой ценой за день — ему ставим подпись «выгоднее».
 * undefined — тариф один или цена за день у всех одинаковая.
 */
export function bestValuePlan(plans: Plan[]): Plan | undefined {
  const perDay = (plan: Plan) => planPrice(plan) / plan.days;
  const sorted = [...plans].sort((a, b) => perDay(a) - perDay(b));
  const [best, next] = sorted;
  return best && next && perDay(best) < perDay(next) ? best : undefined;
}

/** Цена для этого человека: со скидкой по приглашению друга, если она положена */
export function planPrice(plan: Plan): number {
  const own = plan.price_stars_for_you;
  return typeof own === 'number' && own > 0 && own < plan.price_stars ? own : plan.price_stars;
}

/**
 * Скидка на тариф в процентах; 0 — цена обычная. Процент от бэкенда (discount_percent),
 * без него — из самих цен
 */
export function planDiscount(plan: Plan, discountPercent?: number): number {
  const price = planPrice(plan);
  if (price >= plan.price_stars) return 0;
  if (discountPercent && discountPercent > 0) return discountPercent;
  return Math.round((1 - price / plan.price_stars) * 100);
}
