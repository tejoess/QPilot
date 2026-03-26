/**
 * store/bloomStore.ts
 * Bloom's Taxonomy percentage distribution (all 6 levels must sum to 100).
 * setLevel() auto-redistributes the delta across other levels so total stays 100.
 */

import { create } from "zustand";

export type BloomKey = "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create";

export interface BloomLevels {
    remember: number;
    understand: number;
    apply: number;
    analyze: number;
    evaluate: number;
    create: number;
}

const BLOOM_KEYS: BloomKey[] = ["remember", "understand", "apply", "analyze", "evaluate", "create"];

const DEFAULT_LEVELS: BloomLevels = {
    remember: 20,
    understand: 30,
    apply: 30,
    analyze: 20,
    evaluate: 0,
    create: 0,
};

interface BloomState {
    bloomLevels: BloomLevels;
    // Sets one level; redistributes the change across all other levels proportionally
    setLevel: (key: BloomKey, newValue: number) => void;
    reset: () => void;
    getTotal: () => number;
}

export const useBloomStore = create<BloomState>((set, get) => ({
    bloomLevels: { ...DEFAULT_LEVELS },

    setLevel: (key, newValue) => {
        set((state) => {
            const prev = state.bloomLevels;
            const othersTotal = BLOOM_KEYS.filter((k) => k !== key).reduce((s, k) => s + prev[k], 0);

            // Calculate the maximum allowed value for this key without exceeding 100 overall
            const maxAllowed = Math.max(0, 100 - othersTotal);
            // Clamp the new value between 0 and maxAllowed
            const clamped = Math.max(0, Math.min(maxAllowed, Math.round(newValue)));

            return { bloomLevels: { ...prev, [key]: clamped } };
        });
    },

    reset: () => set({ bloomLevels: { ...DEFAULT_LEVELS } }),

    getTotal: () => BLOOM_KEYS.reduce((s, k) => s + get().bloomLevels[k], 0),
}));
