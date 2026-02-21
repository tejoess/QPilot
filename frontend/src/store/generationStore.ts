/**
 * store/generationStore.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Zustand store for the Teacher Input Agent and overall generation state.
 * Manages custom instructions and the subprocess state of the final trigger.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { create } from "zustand";

export type GenerationStatus = "idle" | "running" | "completed" | "failed";

export interface SubprocessStep {
    id: number;
    label: string;
    status: "pending" | "running" | "completed" | "failed";
}

interface GenerationState {
    teacherInput: string;
    status: GenerationStatus;
    currentStepIndex: number;
    steps: SubprocessStep[];
    error: string | null;

    // Actions
    setTeacherInput: (input: string) => void;
    setStatus: (status: GenerationStatus) => void;
    updateStep: (index: number, status: SubprocessStep["status"]) => void;
    setError: (msg: string | null) => void;
    startGeneration: () => void;
    reset: () => void;
}

const INITIAL_STEPS: SubprocessStep[] = [
    { id: 0, label: "Validating Inputs", status: "pending" },
    { id: 1, label: "Initiating AI Generation", status: "pending" },
    { id: 2, label: "Generating Questions", status: "pending" },
    { id: 3, label: "Applying Bloom Distribution", status: "pending" },
    { id: 4, label: "Formatting Paper", status: "pending" },
    { id: 5, label: "Finalizing Output", status: "pending" },
    { id: 6, label: "Completed", status: "pending" },
];

export const useGenerationStore = create<GenerationState>((set) => ({
    teacherInput: "",
    status: "idle",
    currentStepIndex: 0,
    steps: INITIAL_STEPS,
    error: null,

    setTeacherInput: (teacherInput) => set({ teacherInput }),

    setStatus: (status) => set({ status }),

    updateStep: (index, status) => set((state) => {
        const newSteps = [...state.steps];
        if (newSteps[index]) {
            newSteps[index] = { ...newSteps[index], status };
        }
        return { steps: newSteps, currentStepIndex: index };
    }),

    setError: (error) => set({ error }),

    startGeneration: () => set((state) => ({
        status: "running",
        error: null,
        steps: INITIAL_STEPS.map((s, i) => i === 0 ? { ...s, status: "running" } : s)
    })),

    reset: () => set({
        teacherInput: "",
        status: "idle",
        currentStepIndex: 0,
        steps: INITIAL_STEPS,
        error: null,
    }),
}));
