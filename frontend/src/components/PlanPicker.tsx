import { useId } from 'react';
import type { Plan } from '../api/types';
import { plural } from '../lib/format';
import { bestValuePlan } from '../lib/premium';
import { haptic } from '../lib/telegram';
import { useI18n } from '../providers/I18nProvider';

interface PlanPickerProps {
  /** Тарифы от короткого к длинному */
  plans: Plan[];
  selectedId: string;
  onSelect: (id: string) => void;
  disabled?: boolean;
}

const CARD_CLASS =
  'plan-picker__card relative flex min-w-0 flex-1 flex-col items-center gap-1 rounded-[var(--radius-lg)] border-2 px-3 py-4 text-center shadow-[var(--shadow-sm)] transition-colors duration-200';

/**
 * Выбор срока Premium: карточки «7 дней — 100 ⭐» / «30 дней — 250 ⭐» из plans.
 * Один тариф — одна карточка без переключателя.
 */
export default function PlanPicker({ plans, selectedId, onSelect, disabled }: PlanPickerProps) {
  const { t, lang } = useI18n();
  const pt = t.premium;
  const name = useId();
  const best = bestValuePlan(plans);

  const body = (plan: Plan) => (
    <>
      <span className="plan-picker__days text-sm font-medium text-[var(--text-secondary)]">
        {plural(pt.days, plan.days, lang)}
      </span>
      <span className="plan-picker__price text-xl font-bold text-[var(--text-primary)]">
        {plan.price_stars} ⭐
      </span>
      {plan.id === best?.id && (
        <span className="plan-picker__best rounded-full bg-[var(--accent)]/15 px-2 py-0.5 text-xs font-semibold text-[var(--text-primary)]">
          {pt.best_value}
        </span>
      )}
    </>
  );

  const [single] = plans;
  if (plans.length === 1 && single) {
    return (
      <section className="plan-picker flex" aria-label={pt.choose_plan}>
        <p className={`${CARD_CLASS} border-[var(--primary)] bg-[var(--surface)]`}>{body(single)}</p>
      </section>
    );
  }

  return (
    <fieldset className="plan-picker min-w-0 border-0 p-0" disabled={disabled}>
      <legend className="mb-3 p-0 text-lg font-semibold">{pt.choose_plan}</legend>
      <div className="flex gap-3">
        {plans.map((plan) => {
          const selected = plan.id === selectedId;
          return (
            // Настоящие radio: стрелки и скринридер работают без своего кода
            <label
              key={plan.id}
              className={`${CARD_CLASS} cursor-pointer has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-[var(--primary)] has-[:disabled]:cursor-default has-[:disabled]:opacity-70 ${
                selected
                  ? 'border-[var(--primary)] bg-[var(--surface-hover)]'
                  : 'border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-hover)]'
              }`}
            >
              <input
                type="radio"
                name={name}
                value={plan.id}
                checked={selected}
                className="sr-only"
                onChange={() => {
                  haptic('selection');
                  onSelect(plan.id);
                }}
              />
              {body(plan)}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
