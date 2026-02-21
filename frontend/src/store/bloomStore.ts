/**
 * store/bloomStore.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Zustand store for the Blooxanomy (Bloom's Taxonomy) Agent.
 * Manages cognitive level distribution and subprocess steps.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { create } from "zustand";

export type BloomStatus = "idle" | "running" | "completed" | "failed";

export interface BloomLevels {
    remember: number;
    understand: number;
    apply: number;
    analyze: number;
    evaluate: number;
    create: number;
}

export interface SubprocessStep {
    id: number;
    label: string;
    status: "pending" | "running" | "completed" | "failed";
}

interface BloomState {
    bloomLevels: BloomLevels;
    status: BloomStatus;
    currentStepIndex: number;
    steps: SubprocessStep[];
    error: string | null;

    // Actions
    setLevel: (level: keyof BloomLevels, value: number) => void;
    setBloomLevels: (levels: BloomLevels) => void;
    setStatus: (status: BloomStatus) => void;
    updateStep: (index: number, status: SubprocessStep["status"]) => void;
    reset: () => void;
    startBloomProcess: () => void;
    setError: (msg: string | null) => void;
    getTotalAssigned: () => number;
}

const INITIAL_STEPS: SubprocessStep[] = [
    { id: 0, label: "Validating Distribution", status: "pending" },
    { id: 1, label: "Mapping Questions to Levels", status: "pending" },
    { id: 2, label: "Adjusting Difficulty", status: "pending" },
    { id: 3, label: "Completed", status: "pending" },
];

const INITIAL_LEVELS: BloomLevels = {
    remember: 0,
    understand: 0,
    apply: 0,
    analyze: 0,
    evaluate: 0,
    create: 0,
};

export const useBloomStore = create<BloomState>((set, get) => ({
    bloomLevels: INITIAL_LEVELS,
    status: "idle",
    currentStepIndex: 0,
    steps: INITIAL_STEPS,
    error: null,

    setLevel: (level, value) => set((state) => ({
        bloomLevels: { ...state.bloomLevels, [level]: Math.max(0, value) }
    })),

    setBloomLevels: (bloomLevels) => set({ bloomLevels }),

    setStatus: (status) => set({ status }),

    updateStep: (index, status) => set((state) => {
        const newSteps = [...state.steps];
        if (newSteps[index]) {
            newSteps[index] = { ...newSteps[index], status };
        }
        return { steps: newSteps, currentStepIndex: index };
    }),

    setError: (error) => set({ error }),

    getTotalAssigned: () => {
        const l = get().bloomLevels;
        return l.remember + l.understand + l.apply + l.analyze + l.evaluate + l.create;
    },

    reset: () => set({
        bloomLevels: INITIAL_LEVELS,
        status: "idle",
        currentStepIndex: 0,
        steps: INITIAL_STEPS,
        error: null
    }),

    startBloomProcess: () => set((state) => ({
        status: "running",
        currentStepIndex: 0,
        steps: INITIAL_STEPS.map((s, i) => i === 0 ? { ...s, status: "running" } : s),
        error: null
    })),
}));
