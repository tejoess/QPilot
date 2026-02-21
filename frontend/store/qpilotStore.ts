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

export interface ChatMessage {
    id: string;
    sender: string;
    role: "teacher" | "orchestrator" | "agent";
    content: string;
    timestamp: number;
}

interface QPilotState {
    status: "idle" | "running" | "completed" | "failed";
    agents: Agent[];
    activeAgentIndex: number;
    verticalProgress: number;
    paperContent: PaperSection[];

    // Orchestrator State
    pipelineStage: number;
    activeAgent: string | null;
    agentMode: {
        syllabus: "auto" | "manual";
        pyq: "auto" | "manual";
        bloom: "auto" | "manual";
        pattern: "auto" | "manual";
        teacher: "auto" | "manual";
    };
    agentStatuses: {
        syllabus: AgentStatus;
        pyq: AgentStatus;
        bloom: AgentStatus;
        pattern: AgentStatus;
        generation: AgentStatus;
    };
    chatMessages: ChatMessage[];

    // Actions
    setStatus: (status: QPilotState["status"]) => void;
    updateAgent: (index: number, updates: Partial<Agent>) => void;
    setActiveAgentIndex: (index: number) => void;
    setVerticalProgress: (progress: number) => void;
    addQuestion: (sectionTitle: string, question: Omit<Question, "id">) => void;

    // Orchestrator Actions
    emitMessage: (sender: string, role: ChatMessage["role"], content: string) => void;
    setAgentStatus: (agent: keyof QPilotState["agentStatuses"], status: AgentStatus) => void;
    triggerNextAgent: () => void;
    runAutoFillDemo: () => void;

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

    // Orchestrator Initial State
    pipelineStage: 0,
    activeAgent: null,
    agentMode: {
        syllabus: "auto",
        pyq: "auto",
        bloom: "manual",
        pattern: "manual",
        teacher: "manual"
    },
    agentStatuses: {
        syllabus: "idle",
        pyq: "idle",
        bloom: "idle",
        pattern: "idle",
        generation: "idle",
    },
    chatMessages: [],

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

    // Orchestrator Actions
    emitMessage: (sender, role, content) => set((state) => ({
        chatMessages: [
            ...state.chatMessages,
            { id: crypto.randomUUID(), sender, role, content, timestamp: Date.now() }
        ]
    })),

    setAgentStatus: (agent, status) => set((state) => {
        const statuses = { ...state.agentStatuses, [agent]: status };

        // Map store key back to agents array index
        const indexMap: Record<string, number> = {
            syllabus: 0,
            pyq: 1,
            bloom: 2,
            pattern: 3,
            generation: 4
        };

        const index = indexMap[agent];
        const newAgents = [...state.agents];
        if (newAgents[index]) {
            newAgents[index] = { ...newAgents[index], status };
        }

        return { agentStatuses: statuses, agents: newAgents };
    }),

    triggerNextAgent: () => {
        const { activeAgentIndex, setActiveAgentIndex, agentMode } = get();
        const nextIndex = activeAgentIndex + 1;

        if (nextIndex < 5) {
            const indexMap: Record<number, keyof QPilotState["agentMode"]> = {
                0: "syllabus",
                1: "pyq",
                2: "bloom",
                3: "pattern",
                4: "teacher"
            };

            const nextAgentKey = indexMap[nextIndex];

            // Advance highlight
            setActiveAgentIndex(nextIndex);

            // If the next agent is manual, we DO NOT auto-trigger.
            // Component level will handle the rest.
        }
    },

    runAutoFillDemo: () => {
        const { status, emitMessage, reset } = get();
        if (status !== "idle") return;

        reset();
        emitMessage("Orchestrator", "orchestrator", "Demo data loaded. Starting generation pipeline...");
    },

    reset: () => set({
        status: "idle",
        agents: INITIAL_AGENTS,
        activeAgentIndex: -1,
        verticalProgress: 0,
        paperContent: [],
        pipelineStage: 0,
        activeAgent: null,
        agentMode: {
            syllabus: "auto",
            pyq: "auto",
            bloom: "manual",
            pattern: "manual",
            teacher: "manual"
        },
        agentStatuses: {
            syllabus: "idle",
            pyq: "idle",
            bloom: "idle",
            pattern: "idle",
            generation: "idle",
        },
        chatMessages: [],
    }),
}));
