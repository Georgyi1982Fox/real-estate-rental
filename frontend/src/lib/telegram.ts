// Обёртка над Telegram Web App SDK (скрипт подключён в index.html)

type HapticImpact = 'light' | 'medium' | 'heavy' | 'rigid' | 'soft';
type HapticNotification = 'success' | 'error' | 'warning';
export type HapticType = HapticImpact | HapticNotification;
type ColorScheme = 'light' | 'dark';

interface TelegramWebApp {
  initData: string;
  colorScheme: ColorScheme;
  ready(): void;
  expand(): void;
  onEvent(event: 'themeChanged', callback: () => void): void;
  openLink(url: string): void;
  openTelegramLink(url: string): void;
  BackButton: {
    show(): void;
    hide(): void;
    onClick(callback: () => void): void;
    offClick(callback: () => void): void;
  };
  HapticFeedback: {
    impactOccurred(style: HapticImpact): void;
    notificationOccurred(type: HapticNotification): void;
  };
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

const THEME_COLOR: Record<ColorScheme, string> = { light: '#F8FAFC', dark: '#0F172A' };

/** WebApp только если мы реально внутри Telegram (вне его SDK тоже создаёт объект, но без initData) */
export function getWebApp(): TelegramWebApp | null {
  const webApp = window.Telegram?.WebApp;
  return webApp && webApp.initData ? webApp : null;
}

function syncThemeColorMeta(scheme: ColorScheme): void {
  document.getElementById('theme-color-meta')?.setAttribute('content', THEME_COLOR[scheme]);
}

function applyColorScheme(scheme: ColorScheme): void {
  document.documentElement.dataset.telegramTheme = scheme;
  syncThemeColorMeta(scheme);
}

/** Вызывается один раз до рендера React */
export function initTelegram(): void {
  const webApp = getWebApp();
  if (!webApp) {
    // Вне Telegram (обычный браузер) следуем системной теме
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    syncThemeColorMeta(media.matches ? 'dark' : 'light');
    media.addEventListener('change', (event) => syncThemeColorMeta(event.matches ? 'dark' : 'light'));
    return;
  }

  webApp.ready();
  webApp.expand();
  applyColorScheme(webApp.colorScheme);
  webApp.onEvent('themeChanged', () => applyColorScheme(webApp.colorScheme));
}

export function haptic(type: HapticType = 'light'): void {
  const feedback = getWebApp()?.HapticFeedback;
  if (!feedback) return;
  if (type === 'success' || type === 'error' || type === 'warning') {
    feedback.notificationOccurred(type);
  } else {
    feedback.impactOccurred(type);
  }
}

/**
 * Открыть ссылку по правилам Telegram: t.me → openTelegramLink, внешняя → openLink,
 * своя (тот же origin) → навигация роутера без перезагрузки.
 */
export function openLink(url: string, navigateInternal: (path: string) => void): void {
  let target: URL;
  try {
    target = new URL(url, window.location.href);
  } catch {
    return;
  }
  if (target.protocol !== 'https:' && target.protocol !== 'http:') return;

  if (target.origin === window.location.origin) {
    navigateInternal(target.pathname + target.search + target.hash);
    return;
  }

  const webApp = getWebApp();
  if (webApp && target.hostname === 't.me') {
    webApp.openTelegramLink(target.href);
  } else if (webApp) {
    webApp.openLink(target.href);
  } else {
    window.open(target.href, '_blank', 'noopener');
  }
}
