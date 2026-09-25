// Обёртка над Telegram Web App SDK (скрипт подключён в index.html).
// Вне Telegram (обычный браузер) все функции безопасно ничего не делают — приложение работает как сайт.

type HapticImpact = 'light' | 'medium' | 'heavy' | 'rigid' | 'soft';
type HapticNotification = 'success' | 'error' | 'warning';
export type HapticType = HapticImpact | HapticNotification | 'selection';
type ColorScheme = 'light' | 'dark';

/** Пользователь из initDataUnsafe — только для UI; доверять можно лишь проверенному бэкендом initData */
export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
  photo_url?: string;
}

export interface MainButtonParams {
  text?: string;
  color?: string;
  text_color?: string;
  is_active?: boolean;
  is_visible?: boolean;
}

interface TelegramMainButton {
  setParams(params: MainButtonParams): void;
  onClick(callback: () => void): void;
  offClick(callback: () => void): void;
  showProgress(leaveActive?: boolean): void;
  hideProgress(): void;
}

interface TelegramWebApp {
  initData: string;
  initDataUnsafe: { user?: TelegramUser };
  version: string;
  colorScheme: ColorScheme;
  isVersionAtLeast(version: string): boolean;
  ready(): void;
  expand(): void;
  disableVerticalSwipes?(): void;
  setHeaderColor(color: string): void;
  setBackgroundColor(color: string): void;
  setBottomBarColor?(color: string): void;
  onEvent(event: 'themeChanged', callback: () => void): void;
  openLink(url: string): void;
  openTelegramLink(url: string): void;
  MainButton: TelegramMainButton;
  BackButton: {
    show(): void;
    hide(): void;
    onClick(callback: () => void): void;
    offClick(callback: () => void): void;
  };
  HapticFeedback: {
    impactOccurred(style: HapticImpact): void;
    notificationOccurred(type: HapticNotification): void;
    selectionChanged(): void;
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

export function isInTelegram(): boolean {
  return getWebApp() !== null;
}

/** Подписанная строка initData — уходит на бэкенд в заголовке X-Telegram-Init-Data */
export function getInitData(): string {
  return getWebApp()?.initData ?? '';
}

export function getTelegramUser(): TelegramUser | null {
  return getWebApp()?.initDataUnsafe.user ?? null;
}

/** Методы SDK, появившиеся в новых версиях Bot API, вызываем только если клиент их поддерживает */
function supports(webApp: TelegramWebApp, version: string): boolean {
  return webApp.isVersionAtLeast(version);
}

function syncThemeColorMeta(scheme: ColorScheme): void {
  document.getElementById('theme-color-meta')?.setAttribute('content', THEME_COLOR[scheme]);
}

function applyColorScheme(webApp: TelegramWebApp): void {
  const scheme = webApp.colorScheme;
  const color = THEME_COLOR[scheme];
  document.documentElement.dataset.telegramTheme = scheme;
  syncThemeColorMeta(scheme);
  // Шапка и фон самого Telegram — в цвет нашего фона, чтобы не было «шва»
  if (supports(webApp, '6.1')) {
    webApp.setHeaderColor(color);
    webApp.setBackgroundColor(color);
  }
  if (supports(webApp, '7.10')) webApp.setBottomBarColor?.(color);
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
  // Вертикальный свайп закрывает мини-апп — мешает скроллу страниц и свайпу галереи
  if (supports(webApp, '7.7')) webApp.disableVerticalSwipes?.();
  applyColorScheme(webApp);
  webApp.onEvent('themeChanged', () => applyColorScheme(webApp));
  // Safe area: SDK сам пишет --tg-safe-area-inset-* и --tg-content-safe-area-inset-*,
  // theme.css собирает из них --safe-*; ничего вручную обновлять не нужно
}

export function haptic(type: HapticType = 'light'): void {
  const feedback = getWebApp()?.HapticFeedback;
  if (!feedback) return;
  if (type === 'selection') {
    feedback.selectionChanged();
  } else if (type === 'success' || type === 'error' || type === 'warning') {
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
