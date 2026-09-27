/** Логотип Telegram (бумажный самолётик), цвет — currentColor */
export default function TelegramIcon({ className = 'size-5' }: { className?: string }) {
  return (
    <svg className={`telegram-icon shrink-0 ${className}`} viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M21.94 4.3a1.3 1.3 0 0 0-1.76-1.43L2.9 9.53c-1.18.46-1.17 1.12-.21 1.41l4.43 1.38 1.7 5.23c.21.58.1.81.71.81.47 0 .68-.21.94-.47l2.26-2.2 4.7 3.47c.86.48 1.49.23 1.7-.8l3.08-14.5zM8.5 13.9l9.1-5.74c.45-.27.87-.12.53.19l-7.8 7.03-.3 3.24-1.53-4.72z"
      />
    </svg>
  );
}
