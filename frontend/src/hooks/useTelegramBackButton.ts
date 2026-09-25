import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getWebApp, haptic } from '../lib/telegram';

/** Нативная кнопка «Назад» Telegram, пока страница смонтирована; без истории — переход на fallback */
export function useTelegramBackButton(fallbackPath = '/'): void {
  const navigate = useNavigate();

  useEffect(() => {
    const backButton = getWebApp()?.BackButton;
    if (!backButton) return;

    const handleClick = () => {
      haptic('light');
      // React Router хранит индекс записи истории в history.state.idx
      const index = (window.history.state as { idx?: number } | null)?.idx ?? 0;
      if (index > 0) {
        navigate(-1);
      } else {
        navigate(fallbackPath, { replace: true });
      }
    };

    backButton.show();
    backButton.onClick(handleClick);
    return () => {
      backButton.offClick(handleClick);
      backButton.hide();
    };
  }, [navigate, fallbackPath]);
}
