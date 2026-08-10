import { create } from 'zustand';
import type { ToastTone } from '@/components/ui';

interface UiState {
  toast: { tone: ToastTone; message: string } | null;
  sidebarOpen: boolean;
  notify: (tone: ToastTone, message: string) => void;
  dismiss: () => void;
  toggleSidebar: () => void;
}

export const useUiStore = create<UiState>((set) => ({
  toast: null,
  sidebarOpen: true,
  notify: (tone, message) => set({ toast: { tone, message } }),
  dismiss: () => set({ toast: null }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
}));
