/**
 * store/projectStore.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Zustand store for the Builder Stage page.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { create } from "zustand";
import type { Project, Section } from "@/types/api";

interface ProjectStore {
    project: Project | null;
    sections: Section[];
    isLoadingProject: boolean;
    isLoadingSections: boolean;
    isSavingProject: boolean;
    projectError: string | null;
    sectionsError: string | null;

    // ── Actions ────────────────────────────────────────────────────────────────
    setProject: (project: Project | null) => void;
    updateProjectLocal: (updates: Partial<Project>) => void;
    setLoadingProject: (v: boolean) => void;
    setSavingProject: (v: boolean) => void;
    setProjectError: (msg: string | null) => void;

    setSections: (sections: Section[]) => void;
    addSectionLocal: (section: Section) => void;
    updateSectionLocal: (section: Section) => void;
    removeSectionLocal: (sectionId: string) => void;
    setLoadingSections: (v: boolean) => void;
    setSectionsError: (msg: string | null) => void;

    resetBuilder: () => void;

    // ── Computed ──────────────────────────────────────────────────────────────
    getTotalSectionMarks: () => number;
    getTotalQuestions: () => number;
    isValid: () => boolean;
}

const initialState = {
    project: null,
    sections: [],
    isLoadingProject: false,
    isLoadingSections: false,
    isSavingProject: false,
    projectError: null,
    sectionsError: null,
};

export const useProjectStore = create<ProjectStore>()((set, get) => ({
    ...initialState,

    setProject: (project) => set({ project }),
    updateProjectLocal: (updates) => set((state) => ({
        project: state.project ? { ...state.project, ...updates } : null
    })),
    setLoadingProject: (v) => set({ isLoadingProject: v }),
    setSavingProject: (v) => set({ isSavingProject: v }),
    setProjectError: (msg) => set({ projectError: msg }),

    setSections: (sections) =>
        set({ sections: [...sections].sort((a, b) => a.order - b.order) }),

    addSectionLocal: (section) =>
        set((state) => ({
            sections: [...state.sections, section].sort((a, b) => a.order - b.order),
        })),

    updateSectionLocal: (updated) =>
        set((state) => ({
            sections: state.sections
                .map((s) => (s.id === updated.id ? updated : s))
                .sort((a, b) => a.order - b.order),
        })),

    removeSectionLocal: (sectionId) =>
        set((state) => ({
            sections: state.sections.filter((s) => s.id !== sectionId),
        })),

    setLoadingSections: (v) => set({ isLoadingSections: v }),
    setSectionsError: (msg) => set({ sectionsError: msg }),

    resetBuilder: () => set({ ...initialState }),

    // ── Computed ──────────────────────────────────────────────────────────────
    getTotalSectionMarks: () => {
        return get().sections.reduce((sum, s) => sum + (s.totalMarks || 0), 0);
    },
    getTotalQuestions: () => {
        return get().sections.reduce((sum, s) => sum + (s.numQuestions || 0), 0);
    },
    isValid: () => {
        const state = get();
        if (!state.project) return false;
        const totalSectionMarks = state.sections.reduce((sum, s) => sum + (s.totalMarks || 0), 0);
        return totalSectionMarks === state.project.totalMarks && state.sections.length > 0;
    },
}));
