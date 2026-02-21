/**
 * store/pyqStore.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Zustand store for the PYQ Agent workflow.
 * Manages extraction status, current step, and input data for Previous Year Questions.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { create } from "zustand";

export type PyqStatus = "idle" | "running" | "completed" | "failed";

export interface SubprocessStep {
    id: number;
    label: string;
    status: "pending" | "running" | "completed" | "failed";
}

interface PyqState {
    status: PyqStatus;
    currentStepIndex: number;
    steps: SubprocessStep[];
    fileName: string | null;
    textContent: string;
    year: string;
    board: string;
    error: string | null;

    // Actions
    setStatus: (status: PyqStatus) => void;
    setFileName: (name: string | null) => void;
    setTextContent: (text: string) => void;
    setYear: (year: string) => void;
    setBoard: (board: string) => void;
    updateStep: (index: number, status: SubprocessStep["status"]) => void;
    reset: () => void;
    startProcessing: () => void;
    setError: (msg: string | null) => void;
}

const INITIAL_STEPS: SubprocessStep[] = [
    { id: 0, label: "Uploading", status: "pending" },
    { id: 1, label: "Extracting Questions", status: "pending" },
    { id: 2, label: "Categorizing by Topic", status: "pending" },
    { id: 3, label: "Tagging Difficulty", status: "pending" },
    { id: 4, label: "Completed", status: "pending" },
];

export const usePyqStore = create<PyqState>((set) => ({
    status: "idle",
    currentStepIndex: 0,
    steps: INITIAL_STEPS,
    fileName: null,
    textContent: "",
    year: "",
    board: "",
    error: null,

    setStatus: (status) => set({ status }),
    setFileName: (fileName) => set({ fileName }),
    setTextContent: (textContent) => set({ textContent }),
    setYear: (year) => set({ year }),
    setBoard: (board) => set({ board }),

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
        year: "",
        board: "",
        error: null
    }),

    startProcessing: () => set((state) => ({
        status: "running",
        currentStepIndex: 0,
        steps: INITIAL_STEPS.map((s, i) => i === 0 ? { ...s, status: "running" } : s),
        error: null
    })),
}));
