import { create } from "zustand";

type ShareAccessState = {
  token: string | null;
  presentationId: string | null;
  role: string | null;
  setShare: (token: string, presentationId: string, role: string) => void;
  clearShare: () => void;
};

export const useShareAccessStore = create<ShareAccessState>((set) => ({
  token: null,
  presentationId: null,
  role: null,
  setShare: (token, presentationId, role) => set({ token, presentationId, role }),
  clearShare: () => set({ token: null, presentationId: null, role: null }),
}));
