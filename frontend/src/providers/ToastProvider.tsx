import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import Toast from '../components/Toast';
import type { ToastType } from '../components/Toast';

const TOAST_DURATION_MS = 3000;

interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
}

type ShowToast = (message: string, type?: ToastType) => void;

const ToastContext = createContext<ShowToast | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(0);
  const timers = useRef<number[]>([]);

  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach((timer) => window.clearTimeout(timer));
  }, []);

  const showToast = useCallback<ShowToast>((message, type = 'info') => {
    if (!message) return;
    const id = nextId.current++;
    setToasts((items) => [...items, { id, message, type }]);
    timers.current.push(
      window.setTimeout(() => {
        setToasts((items) => items.filter((item) => item.id !== id));
      }, TOAST_DURATION_MS),
    );
  }, []);

  return (
    <ToastContext.Provider value={showToast}>
      {children}
      <section
        className="toast-region pointer-events-none fixed inset-x-4 bottom-[calc(1rem+env(safe-area-inset-bottom))] z-50 mx-auto max-w-md"
        aria-live="polite"
      >
        {toasts.map((toast) => (
          <Toast key={toast.id} message={toast.message} type={toast.type} />
        ))}
      </section>
    </ToastContext.Provider>
  );
}

export function useToast(): ShowToast {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used inside <ToastProvider>');
  return context;
}
