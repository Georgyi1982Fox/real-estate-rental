import Icon from './Icon';

interface AgencyLogoProps {
  url: string | null | undefined;
  /** Размер и скругление: size-6 rounded-full */
  className: string;
  /** Размер иконки-заглушки */
  iconClassName?: string;
}

/** Логотип агентства; не загружен — значок портфеля. Подпись всегда рядом, поэтому alt пустой */
export default function AgencyLogo({ url, className, iconClassName = 'size-4' }: AgencyLogoProps) {
  return (
    <span
      className={`agency-logo grid shrink-0 place-items-center overflow-hidden bg-[var(--surface-hover)] text-[var(--text-secondary)] ${className}`}
    >
      {url ? (
        <img src={url} alt="" loading="lazy" className="h-full w-full object-cover" />
      ) : (
        <Icon name="briefcase" className={iconClassName} />
      )}
    </span>
  );
}
