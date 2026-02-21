/**
 * store/syllabusStore.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Zustand store for the Syllabus Agent workflow.
 * Manages the extraction status, current subprocess step, and polling logic state.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { create } from "zustand";

export type SyllabusStatus = "idle" | "running" | "completed" | "failed";

export interface SubprocessStep {
    id: number;
    label: string;
    status: "pending" | "running" | "completed" | "failed";
}

interface SyllabusState {
    status: SyllabusStatus;
    currentStepIndex: number;
    steps: SubprocessStep[];
    fileName: string | null;
    textContent: string;
    error: string | null;

    // Actions
    setStatus: (status: SyllabusStatus) => void;
    setFileName: (name: string | null) => void;
    setTextContent: (text: string) => void;
    updateStep: (index: number, status: SubprocessStep["status"]) => void;
    reset: () => void;
    startExtraction: () => void;
    setError: (msg: string | null) => void;
}

const INITIAL_STEPS: SubprocessStep[] = [
    { id: 0, label: "Validating Distribution", status: "pending" },
    { id: 1, label: "Mapping Questions to Levels", status: "pending" },
    { id: 2, label: "Adjusting Difficulty", status: "pending" },
    { id: 3, label: "Completed", status: "pending" },
];

export const useSyllabusStore = create<SyllabusState>((set) => ({
    status: "idle",
    currentStepIndex: 0,
    steps: INITIAL_STEPS,
    fileName: null,
    textContent: "",
    error: null,

    setStatus: (status) => set({ status }),
    setFileName: (fileName) => set({ fileName }),
    setTextContent: (textContent) => set({ textContent }),

    updateStep: (index, status) => set((state) => {
        const newSteps = [...state.steps];
        if (newSteps[index]) {
            newSteps[index] = { ...newSteps[index], status };
        }
        return { steps: newSteps, currentStepIndex: index };
    }),

    setError: (error) => set({ error }),

    reset: () => set({
        status: "idle",
        currentStepIndex: 0,
        steps: INITIAL_STEPS,
        fileName: null,
        textContent: "",
        error: null
    }),

    startExtraction: () => set((state) => ({
        status: "running",
        currentStepIndex: 0,
        steps: INITIAL_STEPS.map((s, i) => i === 0 ? { ...s, status: "running" } : s),
        error: null
    })),
}));
