import { create } from "zustand";
import type { Snapshot } from "../contracts/ui";

export type Connection = "connecting" | "connected" | "disconnected";

interface ScreenStore {
  snapshot: Snapshot | null;
  connection: Connection;
  screenDisconnected: boolean;
  pendingRequests: string[];
  setSnapshot: (snapshot: Snapshot) => void;
  setConnection: (connection: Connection) => void;
  setScreenDisconnected: (disconnected: boolean) => void;
  addPending: (id: string) => void;
  removePending: (id: string) => void;
}

export const useScreenStore = create<ScreenStore>((set) => ({
  snapshot: null,
  connection: "connecting",
  screenDisconnected: false,
  pendingRequests: [],
  setSnapshot: (snapshot) => set({ snapshot }),
  setConnection: (connection) => set({ connection }),
  setScreenDisconnected: (screenDisconnected) => set({ screenDisconnected }),
  addPending: (id) =>
    set((state) => ({ pendingRequests: [...state.pendingRequests, id] })),
  removePending: (id) =>
    set((state) => ({
      pendingRequests: state.pendingRequests.filter(
        (pending) => pending !== id,
      ),
    })),
}));
