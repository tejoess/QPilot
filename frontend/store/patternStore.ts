/**
 * store/patternStore.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Zustand store for the Paper Pattern Agent.
 * Tracks sections, marks tally, and subprocess progress.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { create } from "zustand";

export interface PatternSection {
    id: string;
    name: string;
    type: string;
    numQuestions: number;
    marksPerQuestion: number;
    totalMarks: number;
}

export type PatternStatus = "idle" | "running" | "completed" | "failed";

export interface SubprocessStep {
    id: number;
    label: string;
    status: "pending" | "running" | "completed" | "failed";
}

interface PatternState {
    sections: PatternSection[];
    totalMarks: number; // Target marks from metadata
    status: PatternStatus;
    steps: SubprocessStep[];
    error: string | null;

    // Actions
    setTotalMarks: (marks: number) => void;
    addSection: (section: Omit<PatternSection, "id" | "totalMarks">) => void;
    updateSection: (id: string, updates: Partial<PatternSection>) => void;
    deleteSection: (id: string) => void;
    setStatus: (status: PatternStatus) => void;
    updateStep: (index: number, status: SubprocessStep["status"]) => void;
    setError: (msg: string | null) => void;
    reset: () => void;
    startPatternProcess: () => void;
    getTotalAllocated: () => number;
}

const INITIAL_STEPS: SubprocessStep[] = [
    { id: 0, label: "Validating Pattern", status: "pending" },
    { id: 1, label: "Calculating Weightage", status: "pending" },
    { id: 2, label: "Optimizing Distribution", status: "pending" },
    { id: 3, label: "Completed", status: "pending" },
];

export const usePatternStore = create<PatternState>((set, get) => ({
    sections: [],
    totalMarks: 80, // Default fallback
    status: "idle",
    steps: INITIAL_STEPS,
    error: null,

    setTotalMarks: (totalMarks) => set({ totalMarks }),

    addSection: (data) => set((state) => {
        const newSection: PatternSection = {
            ...data,
            id: crypto.randomUUID(),
            totalMarks: data.numQuestions * data.marksPerQuestion
        };
        return { sections: [...state.sections, newSection] };
    }),

    updateSection: (id, updates) => set((state) => {
        const newSections = state.sections.map((s) => {
            if (s.id === id) {
                const updated = { ...s, ...updates };
                updated.totalMarks = updated.numQuestions * updated.marksPerQuestion;
                return updated;
            }
            return s;
        });
        return { sections: newSections };
    }),

    deleteSection: (id) => set((state) => ({
        sections: state.sections.filter((s) => s.id !== id)
    })),

    setStatus: (status) => set({ status }),

    updateStep: (index, status) => set((state) => {
        const newSteps = [...state.steps];
        if (newSteps[index]) {
            newSteps[index] = { ...newSteps[index], status };
        }
        return { steps: newSteps };
    }),

    setError: (error) => set({ error }),

    getTotalAllocated: () => {
        return get().sections.reduce((acc, s) => acc + s.totalMarks, 0);
    },

    reset: () => set({
        sections: [],
        status: "idle",
        steps: INITIAL_STEPS,
        error: null
    }),

    startPatternProcess: () => set((state) => ({
        status: "running",
        error: null,
        steps: INITIAL_STEPS.map((s, i) => i === 0 ? { ...s, status: "running" } : s)
    })),
}));
