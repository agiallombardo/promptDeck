import { useEffect } from "react";
import { useToastStore } from "../stores/toasts";

export function ToastViewport() {
  const items = useToastStore((s) => s.items);
  const dismissToast = useToastStore((s) => s.dismissToast);

  useEffect(() => {
    if (items.length === 0) return;
    const t = window.setTimeout(() => {
      dismissToast(items[0]!.id);
    }, 9000);
    return () => window.clearTimeout(t);
  }, [items, dismissToast]);

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
