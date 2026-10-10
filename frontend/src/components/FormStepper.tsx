import { fillVars } from '../lib/format';
import { useI18n } from '../providers/I18nProvider';

interface FormStepperProps {
  /** Номер шага с единицы */
  current: number;
  total: number;
  /** Название текущего шага */
  title: string;
}

/** Шапка шага формы: «Шаг 2 из 7», название шага и полоса прогресса */
export default function FormStepper({ current, total, title }: FormStepperProps) {
  const { t } = useI18n();
  const label = fillVars(t.hotel_form.step_of, { n: current, total });

  return (
    <header className="form-stepper flex flex-col gap-2">
      <p className="m-0 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
        {label}
      </p>
      <h2 className="m-0 text-xl font-bold tracking-tight">{title}</h2>
      <div
        className="form-stepper__bar flex gap-1"
        role="progressbar"
        aria-label={label}
        aria-valuemin={1}
        aria-valuemax={total}
        aria-valuenow={current}
      >
        {Array.from({ length: total }, (_, index) => (
          <span
            key={index}
            className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${
              index < current ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'
            }`}
            aria-hidden="true"
          />
        ))}
      </div>
    </header>
  );
}
