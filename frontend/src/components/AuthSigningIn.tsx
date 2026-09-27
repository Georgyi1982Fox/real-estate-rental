import { LOGO_URL } from '../lib/config';
import { useI18n } from '../providers/I18nProvider';

/** Экран «Входим…»: логотип с расходящимися кольцами и бегущие точки (анимации — main.css) */
export default function AuthSigningIn() {
  const { t } = useI18n();

  return (
    <section
      className="auth-signing flex flex-col items-center gap-6 text-center"
      aria-labelledby="auth-signing-title"
      aria-busy="true"
    >
      <figure className="auth-signing__logo relative m-0 grid size-24 place-items-center">
        <span className="auth-signing__ring" aria-hidden="true" />
        <span className="auth-signing__ring auth-signing__ring--late" aria-hidden="true" />
        <img
          className="auth-signing__image relative size-20 rounded-full shadow-[var(--shadow-lg)]"
          src={LOGO_URL}
          alt="Bina.ai"
          width={80}
          height={80}
        />
      </figure>
      <div className="auth-signing__text flex flex-col items-center gap-1" role="status">
        <h1 id="auth-signing-title" className="text-2xl font-bold tracking-tight">
          {t.auth.signing_in}
        </h1>
        <p className="text-sm text-[var(--text-secondary)]">{t.auth.signing_in_hint}</p>
      </div>
      <span className="auth-signing__dots flex gap-1.5" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
    </section>
  );
}
