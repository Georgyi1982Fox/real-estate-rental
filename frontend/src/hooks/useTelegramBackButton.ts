import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { getWebApp, haptic } from '../lib/telegram';

// Нативная «Назад» одна на всё приложение, а хотят её страница и открытая поверх модалка.
// Держим стек владельцев: нажатие получает только верхний (модалка важнее страницы),
// кнопка видна, пока стек не пуст.

interface BackEntry {
  /** 1 — модалка, 0 — страница: модалка остаётся сверху, даже если смонтировалась раньше */
  priority: number;
  handler: { current: () => void };
}

const stack: BackEntry[] = [];

function topEntry(): BackEntry | undefined {
  // При равном приоритете главный тот, кто подписался позже
  return stack.reduce<BackEntry | undefined>(
    (top, entry) => (!top || entry.priority >= top.priority ? entry : top),
    undefined,
  );
}

function handleBackClick(): void {
  haptic('light');
  topEntry()?.handler.current();
}

function register(entry: BackEntry): () => void {
  const backButton = getWebApp()?.BackButton;
  if (!backButton) return () => undefined;
  if (stack.length === 0) {
    backButton.onClick(handleBackClick);
    backButton.show();
  }
  stack.push(entry);
  return () => {
    stack.splice(stack.indexOf(entry), 1);
    if (stack.length > 0) return;
    backButton.offClick(handleBackClick);
    backButton.hide();
  };
}

/** Нативная «Назад» вызывает onBack, пока enabled; модалки передают priority = 1 */
export function useTelegramBack(onBack: () => void, enabled = true, priority = 0): void {
  // Актуальный обработчик без переподписки на каждый рендер
  const handler = useRef(onBack);
  useEffect(() => {
    handler.current = onBack;
  });

  useEffect(() => {
    if (!enabled) return;
    return register({ priority, handler });
  }, [enabled, priority]);
}

/** Нативная кнопка «Назад» Telegram, пока страница смонтирована; без истории — переход на fallback */
export function useTelegramBackButton(fallbackPath = '/'): void {
  const navigate = useNavigate();

  useTelegramBack(() => {
    // React Router хранит индекс записи истории в history.state.idx
    const index = (window.history.state as { idx?: number } | null)?.idx ?? 0;
    if (index > 0) {
      navigate(-1);
    } else {
      navigate(fallbackPath, { replace: true });
    }
  });
}
