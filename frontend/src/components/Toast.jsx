import { createContext, useCallback, useContext, useState } from "react";

const ToastContext = createContext(null);

/** Small pop-up messages: const toast = useToast(); toast.success("Saved"); toast.error("Failed"); */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const show = useCallback((message, type) => {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { id, message, type }]);
    setTimeout(() => setToasts((current) => current.filter((t) => t.id !== id)), 4000);
  }, []);

  const [toast] = useState(() => ({
    success: (message) => show(message, "success"),
    error: (message) => show(message, "error"),
  }));

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
