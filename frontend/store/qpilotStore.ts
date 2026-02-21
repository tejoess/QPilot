/**
 * store/qpilotStore.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Zustand store for the QPilot Agent Execution interface.
 * Tracks agent status, active agent index, vertical progress, and paper content.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { create } from "zustand";

export type AgentStatus = "idle" | "running" | "completed" | "failed";

export interface Agent {
    id: string;
    name: string;
    status: AgentStatus;
    progress: number;
    description: string;
}

export interface Question {
    id: string;
    number: number;
    text: string;
    marks: number;
}

export interface PaperSection {
    id: string;
    title: string;
    questions: Question[];
}

interface QPilotState {
    status: "idle" | "running" | "completed" | "failed";
    agents: Agent[];
    activeAgentIndex: number;
    verticalProgress: number; // 0 to 100 representing the entire pipeline
    paperContent: PaperSection[];

    // Actions
    setStatus: (status: QPilotState["status"]) => void;
    updateAgent: (index: number, updates: Partial<Agent>) => void;
    setActiveAgentIndex: (index: number) => void;
    setVerticalProgress: (progress: number) => void;
    addQuestion: (sectionTitle: string, question: Omit<Question, "id">) => void;
    reset: () => void;
}

const INITIAL_AGENTS: Agent[] = [
    { id: "syllabus-fetch", name: "Syllabus Agent", status: "idle", progress: 0, description: "Retrieving official curriculum data" },
    { id: "pyq-fetch", name: "PYQ Agent", status: "idle", progress: 0, description: "Fetching previous year questions" },
    { id: "blueprint-build", name: "Blooxanomy Agent", status: "idle", progress: 0, description: "Designing cognitive weightage" },
    { id: "blueprint-verify", name: "Paper Pattern Agent", status: "idle", progress: 0, description: "Verifying structural constraints" },
    { id: "teacher-input", name: "Teacher Input Agent", status: "idle", progress: 0, description: "Final generation trigger" },
];

export const useQPilotStore = create<QPilotState>((set, get) => ({
    status: "idle",
    agents: INITIAL_AGENTS,
    activeAgentIndex: -1,
    verticalProgress: 0,
    paperContent: [],

    setStatus: (status) => set({ status }),

    updateAgent: (index, updates) => set((state) => {
        const newAgents = [...state.agents];
        newAgents[index] = { ...newAgents[index], ...updates };
        return { agents: newAgents };
    }),

    setActiveAgentIndex: (index) => set((state) => {
        // Also update vertical progress based on index
        const total = state.agents.length;
        const verticalProgress = total > 0 ? ((index + 1) / total) * 100 : 0;
        return { activeAgentIndex: index, verticalProgress };
    }),

    setVerticalProgress: (progress) => set({ verticalProgress: progress }),

    addQuestion: (sectionTitle, questionData) => set((state) => {
        const content = [...state.paperContent];
        let section = content.find(s => s.title === sectionTitle);

        if (!section) {
            section = { id: crypto.randomUUID(), title: sectionTitle, questions: [] };
            content.push(section);
        }

        const newQuestion: Question = {
            ...questionData,
            id: crypto.randomUUID(),
        };

        section.questions = [...section.questions, newQuestion];

        return { paperContent: content };
    }),

    reset: () => set({
        status: "idle",
        agents: INITIAL_AGENTS,
        activeAgentIndex: -1,
        verticalProgress: 0,
        paperContent: [],
    }),
}));
