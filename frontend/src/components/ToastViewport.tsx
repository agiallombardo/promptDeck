import { useEffect, useRef } from "react";
import { useToastStore } from "../stores/toasts";

export function ToastViewport() {
  const items = useToastStore((s) => s.items);
  const dismissToast = useToastStore((s) => s.dismissToast);
  const timersRef = useRef<Map<string, number>>(new Map());

  useEffect(() => {
    const timers = timersRef.current;
    const ids = new Set(items.map((i) => i.id));

    for (const item of items) {
      if (!timers.has(item.id)) {
        const tid = window.setTimeout(() => {
          timers.delete(item.id);
          dismissToast(item.id);
        }, 9000);
        timers.set(item.id, tid);
      }
    }

    for (const [id, tid] of [...timers.entries()]) {
      if (!ids.has(id)) {
        window.clearTimeout(tid);
        timers.delete(id);
      }
    }
  }, [items, dismissToast]);

  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      for (const tid of timers.values()) {
        window.clearTimeout(tid);
      }
      timers.clear();
    };
  }, []);

  if (items.length === 0) return null;

  return (
    <div
      className="pointer-events-none fixed right-4 top-4 z-[100] flex max-w-sm flex-col gap-2"
      aria-live="polite"
    >
      {items.map((t) => (
        <div
          key={t.id}
          className="pointer-events-auto rounded-sharp border border-border bg-bg-elevated p-3 shadow-elevated ring-1 ring-border"
        >
          <p className="font-body text-sm text-text-main">{t.message}</p>
          {t.requestId ? (
            <p className="mt-1 font-mono text-[10px] text-text-muted">
              Request ID: <span className="select-all text-primary">{t.requestId}</span>
            </p>
          ) : null}
          <button
            type="button"
            className="mt-2 font-mono text-[10px] text-text-muted underline hover:text-primary"
            onClick={() => dismissToast(t.id)}
          >
            Dismiss
          </button>
        </div>
      ))}
    </div>
  );
}
