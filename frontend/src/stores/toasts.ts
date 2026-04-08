import { create } from "zustand";

export type ToastLevel = "error" | "info";

export type ToastItem = {
  id: string;
  level: ToastLevel;
  message: string;
  requestId?: string | null;
};

type ToastState = {
  items: ToastItem[];
  pushToast: (t: Omit<ToastItem, "id">) => void;
  dismissToast: (id: string) => void;
};

let seq = 0;

export const useToastStore = create<ToastState>((set) => ({
  items: [],
  pushToast: (t) => {
    const id = `toast-${++seq}`;
    set((s) => ({ items: [...s.items, { ...t, id }] }));
  },
  dismissToast: (id) => set((s) => ({ items: s.items.filter((x) => x.id !== id) })),
}));

export function pushToastFromApiError(err: { message: string; requestId?: string | null }) {
  useToastStore.getState().pushToast({
    level: "error",
    message: err.message,
    requestId: err.requestId ?? null,
  });
}
