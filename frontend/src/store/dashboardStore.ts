/**
 * store/dashboardStore.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Zustand store for Dashboard state, including system statistics, 
 * recent papers list, and the Floating Orchestrator status.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { create } from "zustand";
import { Project } from "@/types/api";

export interface SystemStats {
    totalPapers: number;
    lastGenTime: string;
    avgGenTime: string;
    pyqDbSize: string;
    trends: {
        totalPapers?: string;
    };
}

interface DashboardState {
    systemStats: SystemStats | null;
    recentPapers: Project[];
    orchestratorOpen: boolean;
    isLoading: boolean;

    // Actions
    setSystemStats: (stats: SystemStats) => void;
    setRecentPapers: (papers: Project[]) => void;
    setOrchestratorOpen: (open: boolean) => void;
    setLoading: (loading: boolean) => void;
    reset: () => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
    systemStats: null,
    recentPapers: [],
    orchestratorOpen: false,
    isLoading: true,

    setSystemStats: (systemStats) => set({ systemStats }),
    setRecentPapers: (recentPapers) => set({ recentPapers }),
    setOrchestratorOpen: (orchestratorOpen) => set({ orchestratorOpen }),
    setLoading: (isLoading) => set({ isLoading }),
    reset: () => set({
        systemStats: null,
        recentPapers: [],
        orchestratorOpen: false,
        isLoading: true,
    }),
}));
