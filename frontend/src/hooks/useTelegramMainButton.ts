import { useEffect, useRef } from 'react';
import { getWebApp, haptic } from '../lib/telegram';

interface MainButtonOptions {
  text: string;
  onClick: () => void;
  /** Показывать ли кнопку (например, только когда данные загрузились) */
  visible?: boolean;
  loading?: boolean;
  disabled?: boolean;
}

/** Цвет кнопки берём из темы (--primary), чтобы палитра жила только в theme.css */
function readPrimaryColor(): string {
  return getComputedStyle(document.documentElement).getPropertyValue('--primary').trim();
}

/**
 * Нативная MainButton Telegram, пока компонент смонтирован.
 * Возвращает true, если кнопка используется — тогда HTML-дубль на странице можно скрыть.
 */
export function useTelegramMainButton({
  text,
  onClick,
  visible = true,
  loading = false,
  disabled = false,
}: MainButtonOptions): boolean {
  const mainButton = getWebApp()?.MainButton ?? null;
  // Актуальный обработчик без переподписки на каждый рендер
  const onClickRef = useRef(onClick);
  useEffect(() => {
    onClickRef.current = onClick;
  });

  useEffect(() => {
    if (!mainButton) return;
    const handleClick = () => {
      haptic('medium');
      onClickRef.current();
    };
    mainButton.onClick(handleClick);
    return () => {
      mainButton.offClick(handleClick);
      mainButton.hideProgress();
      mainButton.setParams({ is_visible: false });
    };
  }, [mainButton]);

  useEffect(() => {
    if (!mainButton) return;
    mainButton.setParams({
      text,
      color: readPrimaryColor(),
      text_color: '#FFFFFF',
      is_active: !disabled && !loading,
      is_visible: visible,
    });
    if (loading) {
      mainButton.showProgress(false);
    } else {
      mainButton.hideProgress();
    }
  }, [mainButton, text, visible, loading, disabled]);

  return mainButton !== null;
}
