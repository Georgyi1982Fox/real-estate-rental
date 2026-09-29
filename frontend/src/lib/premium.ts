import type { Plan, SubscriptionLimits } from '../api/types';

// /api/subscription отдаёт лимиты только текущего тарифа, а таблице «Бесплатно / Premium»
// нужны обе колонки: вторую берём отсюда. Эти же значения видит гость (без запроса к API)

// Избранное без ограничений на всех тарифах (TASK-016)
export const FREE_LIMITS: SubscriptionLimits = { favorites: null, searches: 1 };

export const PREMIUM_LIMITS: SubscriptionLimits = { favorites: null, searches: 20 };

export const DEFAULT_PLAN: Plan = {
  id: 'premium_month',
  tier: 'nomad',
  days: 30,
  price_stars: 250,
};

/** План для покупки: первый платный из ответа бэкенда, иначе план по умолчанию */
export function premiumPlan(plans: Plan[] | undefined): Plan {
  return plans?.find((plan) => plan.tier !== 'free' && plan.price_stars > 0) ?? DEFAULT_PLAN;
}
