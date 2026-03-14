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
        const clamped = Math.max(0, Math.min(100, Math.round(newValue)));
        set((state) => {
            const prev = state.bloomLevels;
            const oldValue = prev[key];
            const delta = clamped - oldValue; // how much this key changed
            if (delta === 0) return state;

            // Keys that can absorb the change
            const others = BLOOM_KEYS.filter((k) => k !== key);
            const othersTotal = others.reduce((s, k) => s + prev[k], 0);

            const next = { ...prev, [key]: clamped };

            if (othersTotal === 0) {
                // All other levels are 0 — can only shrink this key, not grow it
                next[key] = Math.min(clamped, 100);
            } else {
                // Distribute -delta proportionally across others
                let remaining = -delta;
                const adjusted = others.map((k) => {
                    const share = Math.round((prev[k] / othersTotal) * (-delta));
                    return { k, share };
                });
                // Apply shares
                adjusted.forEach(({ k, share }) => {
                    next[k] = Math.max(0, prev[k] + share);
                    remaining -= share;
                });
                // Fix any rounding drift on the first adjustable key
                for (const { k } of adjusted) {
                    if (next[k] + remaining >= 0) {
                        next[k] += remaining;
                        break;
                    }
                }
            }

            // Final safety clamp so total = 100
            const total = BLOOM_KEYS.reduce((s, k) => s + next[k], 0);
            if (total !== 100) {
                const largest = BLOOM_KEYS.reduce((a, b) => (next[a] > next[b] ? a : b));
                next[largest] += 100 - total;
            }

            return { bloomLevels: next };
        });
    },

    reset: () => set({ bloomLevels: { ...DEFAULT_LEVELS } }),

    getTotal: () => BLOOM_KEYS.reduce((s, k) => s + get().bloomLevels[k], 0),
}));
