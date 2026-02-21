/**
 * store/processingStore.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Zustand store for managing the paper generation lifecycle.
 * Tracks pipeline steps, logs, and overall progress.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { create } from "zustand";

export type StepStatus = "pending" | "running" | "completed" | "failed";

export interface PipelineStep {
    id: string;
    name: string;
    status: StepStatus;
    description?: string;
}

interface ProcessingState {
    status: "idle" | "generating" | "completed" | "failed";
    progress: number;
    logs: string[];
    steps: PipelineStep[];
    error: string | null;
    resultFilePath: string | null;

    // Actions
    startProcessing: () => void;
    updateStep: (id: string, status: StepStatus) => void;
    addLog: (log: string) => void;
    setProgress: (progress: number) => void;
    setResult: (path: string) => void;
    setError: (msg: string) => void;
    reset: () => void;
}

const INITIAL_STEPS: PipelineStep[] = [
    { id: "1", name: "Syllabus Fetch", status: "pending", description: "Retrieving syllabus data" },
    { id: "2", name: "Syllabus Format", status: "pending", description: "Parsing structure" },
    { id: "3", name: "PYQs Fetch", status: "pending", description: "Fetching previous year questions" },
    { id: "4", name: "PYQs Format", status: "pending", description: "Formatting question bank" },
    { id: "5", name: "Blueprint Build", status: "pending", description: "Constructing paper blueprint" },
    { id: "6", name: "Blueprint Verify", status: "pending", description: "Validating structure against constraints" },
    { id: "7", name: "Select Questions", status: "pending", description: "AI-powered question selection" },
    { id: "8", name: "Verify Paper", status: "pending", description: "Final quality check" },
    { id: "9", name: "Generate Final", status: "pending", description: "Exporting to PDF" },
];

export const useProcessingStore = create<ProcessingState>((set) => ({
    status: "idle",
    progress: 0,
    logs: [],
    steps: INITIAL_STEPS,
    error: null,
    resultFilePath: null,

    startProcessing: () => set({
        status: "generating",
        progress: 0,
        logs: [],
        steps: INITIAL_STEPS.map(s => ({ ...s, status: s.id === "1" ? "running" : "pending" })),
        error: null,
        resultFilePath: null
    }),

    updateStep: (id, status) => set((state) => {
        const newSteps = state.steps.map((s) => (s.id === id ? { ...s, status } : s));

        // Auto-advance logic: if a step completes, start the next one
        if (status === "completed") {
            const currentIdx = state.steps.findIndex(s => s.id === id);
            if (currentIdx < state.steps.length - 1) {
                newSteps[currentIdx + 1].status = "running";
            }
        }

        return { steps: newSteps };
    }),

    addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),

    setProgress: (progress) => set({ progress }),

    setResult: (path) => set({ status: "completed", resultFilePath: path, progress: 100 }),

    setError: (msg) => set({ status: "failed", error: msg }),

    reset: () => set({
        status: "idle",
        progress: 0,
        logs: [],
        steps: INITIAL_STEPS,
        error: null,
        resultFilePath: null
    }),
}));
