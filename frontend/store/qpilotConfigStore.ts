/**
 * store/qpilotConfigStore.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Zustand store for the QPilot Metadata Configuration page.
 * Manages the draft state of a question paper before generation starts.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { create } from "zustand";

export type QuestionType = "mcq" | "short_answer" | "long_answer" | "fill_in_the_blank" | "true_false";
export type Difficulty = "easy" | "medium" | "hard";

export interface QPilotSection {
    id: string;
    title: string;
    type: QuestionType;
    numQuestions: number;
    marksPerQuestion: number;
    difficulty: Difficulty;
}

export interface QPilotMetadata {
    title: string;
    subject: string;
    grade: string;
    board: string;
    totalMarks: number;
    duration: string;
    instructions: string;
}

interface QPilotConfigState {
    metadata: QPilotMetadata;
    sections: QPilotSection[];
    isSubmitting: boolean;

    // Actions
    setMetadata: (updates: Partial<QPilotMetadata>) => void;
    addSection: (section: Omit<QPilotSection, "id">) => void;
    updateSection: (id: string, updates: Partial<QPilotSection>) => void;
    removeSection: (id: string) => void;
    setSubmitting: (isSubmitting: boolean) => void;
    reset: () => void;

    // Computed
    getTotalSectionMarks: () => number;
}

const INITIAL_METADATA: QPilotMetadata = {
    title: "",
    subject: "",
    grade: "",
    board: "CBSE",
    totalMarks: 80,
    duration: "3 Hours",
    instructions: "1. All questions are compulsory.\n2. Read the questions carefully.",
};

export const useQPilotConfigStore = create<QPilotConfigState>((set, get) => ({
    metadata: INITIAL_METADATA,
    sections: [],
    isSubmitting: false,

    setMetadata: (updates) => set((state) => ({
        metadata: { ...state.metadata, ...updates }
    })),

    addSection: (sectionData) => set((state) => ({
        sections: [...state.sections, { ...sectionData, id: crypto.randomUUID() }]
    })),

    updateSection: (id, updates) => set((state) => ({
        sections: state.sections.map((s) => (s.id === id ? { ...s, ...updates } : s))
    })),

    removeSection: (id) => set((state) => ({
        sections: state.sections.filter((s) => s.id !== id)
    })),

    setSubmitting: (isSubmitting) => set({ isSubmitting }),

    reset: () => set({ metadata: INITIAL_METADATA, sections: [], isSubmitting: false }),

    getTotalSectionMarks: () => {
        return get().sections.reduce((sum, s) => sum + (s.numQuestions * s.marksPerQuestion), 0);
    },
}));
