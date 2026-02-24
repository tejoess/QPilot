/**
 * store/orchestrationStore.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Orchestration store for managing the 3-step workflow:
 * 1. Analyze Syllabus → 2. Analyze PYQs → 3. Generate Paper
 * 
 * Features:
 * - Session ID tracking for all 3 steps
 * - WebSocket connection management for real-time updates
 * - Progress and log message storage
 * - Sequential execution queue
 * - Auto-trigger next step on completion
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { create } from "zustand";

// ─── Types ────────────────────────────────────────────────────────────────────

export type WorkflowStep = "syllabus" | "pyqs" | "paper";
export type StepStatus = "idle" | "running" | "completed" | "failed";

export interface ProgressMessage {
    type: "progress";
    timestamp: string;
    step: string;
    status: string;
    progress: number; // 0-100
    details: string;
}

export interface LogMessage {
    type: "log";
    timestamp: string;
    level: "info" | "warning" | "error";
    message: string;
}

export interface CompletionMessage {
    type: "completion";
    timestamp: string;
    success: boolean;
    data: Record<string, any>;
}

export type WebSocketMessage = ProgressMessage | LogMessage | CompletionMessage;

export interface WorkflowState {
    // Session IDs
    syllabusSessionId: string | null;
    pyqsSessionId: string | null;
    paperSessionId: string | null;

    // Step statuses
    syllabusStatus: StepStatus;
    pyqsStatus: StepStatus;
    paperStatus: StepStatus;

    // Current progress
    currentStep: WorkflowStep | null;
    currentProgress: number; // 0-100

    // WebSocket state
    ws: WebSocket | null;
    isConnected: boolean;
    
    // Messages
    logs: LogMessage[];
    progressUpdates: ProgressMessage[];
    
    // Data
    syllabusData: any | null;
    pyqsData: any | null;
    paperData: any | null;

    // Errors
    error: string | null;

    // Queue for sequential execution
    pendingSteps: WorkflowStep[];

    // ─── Actions ──────────────────────────────────────────────────────────────

    // Session management
    setSyllabusSession: (sessionId: string) => void;
    setPyqsSession: (sessionId: string) => void;
    setPaperSession: (sessionId: string) => void;

    // Status updates
    setSyllabusStatus: (status: StepStatus) => void;
    setPyqsStatus: (status: StepStatus) => void;
    setPaperStatus: (status: StepStatus) => void;

    // WebSocket management
    connectWebSocket: (sessionId: string) => void;
    disconnectWebSocket: () => void;
    addLog: (log: LogMessage) => void;
    addProgress: (progress: ProgressMessage) => void;

    // Data storage
    setSyllabusData: (data: any) => void;
    setPyqsData: (data: any) => void;
    setPaperData: (data: any) => void;

    // Workflow control
    startWorkflow: (step: WorkflowStep) => void;
    completeStep: (step: WorkflowStep, data?: any) => void;
    failStep: (step: WorkflowStep, error: string) => void;
    queueStep: (step: WorkflowStep) => void;
    processQueue: () => void;

    // Reset
    reset: () => void;
    clearLogs: () => void;
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useOrchestrationStore = create<WorkflowState>((set, get) => ({
    // Initial state
    syllabusSessionId: null,
    pyqsSessionId: null,
    paperSessionId: null,

    syllabusStatus: "idle",
    pyqsStatus: "idle",
    paperStatus: "idle",

    currentStep: null,
    currentProgress: 0,

    ws: null,
    isConnected: false,

    logs: [],
    progressUpdates: [],

    syllabusData: null,
    pyqsData: null,
    paperData: null,

    error: null,
    pendingSteps: [],

    // ─── Session Management ───────────────────────────────────────────────────

    setSyllabusSession: (sessionId) => set({ syllabusSessionId: sessionId }),
    setPyqsSession: (sessionId) => set({ pyqsSessionId: sessionId }),
    setPaperSession: (sessionId) => set({ paperSessionId: sessionId }),

    // ─── Status Updates ───────────────────────────────────────────────────────

    setSyllabusStatus: (status) => set({ syllabusStatus: status }),
    setPyqsStatus: (status) => set({ pyqsStatus: status }),
    setPaperStatus: (status) => set({ paperStatus: status }),

    // ─── WebSocket Management ─────────────────────────────────────────────────

    connectWebSocket: (sessionId) => {
        const state = get();
        
        // Disconnect existing connection
        if (state.ws) {
            state.ws.close();
        }

        const wsUrl = `ws://127.0.0.1:8000/ws/${sessionId}`;
        console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log(`✅ WebSocket connected: ${sessionId}`);
            set({ ws, isConnected: true });
        };

        ws.onmessage = (event) => {
            try {
                const message: WebSocketMessage = JSON.parse(event.data);
                
                if (message.type === "progress") {
                    get().addProgress(message);
                    set({ currentProgress: message.progress });
                } else if (message.type === "log") {
                    get().addLog(message);
                } else if (message.type === "completion") {
                    console.log("✅ Workflow step completed:", message.data);
                    // Process next queued step
                    setTimeout(() => get().processQueue(), 500);
                }
            } catch (err) {
                console.error("Failed to parse WebSocket message:", err);
            }
        };

        ws.onerror = (error) => {
            console.error("❌ WebSocket error:", error);
            set({ isConnected: false, error: "WebSocket connection failed" });
        };

        ws.onclose = () => {
            console.log("🔌 WebSocket disconnected");
            set({ ws: null, isConnected: false });
        };

        set({ ws });
    },

    disconnectWebSocket: () => {
        const state = get();
        if (state.ws) {
            state.ws.close();
            set({ ws: null, isConnected: false });
        }
    },

    addLog: (log) => {
        set((state) => ({
            logs: [...state.logs, log].slice(-100) // Keep last 100 logs
        }));
    },

    addProgress: (progress) => {
        set((state) => ({
            progressUpdates: [...state.progressUpdates, progress].slice(-50) // Keep last 50 updates
        }));
    },

    // ─── Data Storage ─────────────────────────────────────────────────────────

    setSyllabusData: (data) => set({ syllabusData: data }),
    setPyqsData: (data) => set({ pyqsData: data }),
    setPaperData: (data) => set({ paperData: data }),

    // ─── Workflow Control ─────────────────────────────────────────────────────

    startWorkflow: (step) => {
        console.log(`🚀 Starting workflow step: ${step}`);
        set({ currentStep: step, currentProgress: 0, error: null });

        if (step === "syllabus") {
            get().setSyllabusStatus("running");
        } else if (step === "pyqs") {
            get().setPyqsStatus("running");
        } else if (step === "paper") {
            get().setPaperStatus("running");
        }
    },

    completeStep: (step, data) => {
        console.log(`✅ Completed workflow step: ${step}`, data);

        if (step === "syllabus") {
            get().setSyllabusStatus("completed");
            if (data) get().setSyllabusData(data);
        } else if (step === "pyqs") {
            get().setPyqsStatus("completed");
            if (data) get().setPyqsData(data);
        } else if (step === "paper") {
            get().setPaperStatus("completed");
            if (data) get().setPaperData(data);
        }

        set({ currentProgress: 100 });
        
        // Process next step in queue
        setTimeout(() => get().processQueue(), 1000);
    },

    failStep: (step, error) => {
        console.error(`❌ Failed workflow step: ${step}`, error);

        if (step === "syllabus") {
            get().setSyllabusStatus("failed");
        } else if (step === "pyqs") {
            get().setPyqsStatus("failed");
        } else if (step === "paper") {
            get().setPaperStatus("failed");
        }

        set({ error, currentStep: null });
    },

    queueStep: (step) => {
        set((state) => ({
            pendingSteps: [...state.pendingSteps, step]
        }));
        console.log(`📋 Queued step: ${step}`);
    },

    processQueue: () => {
        const state = get();
        
        if (state.pendingSteps.length === 0) {
            console.log("✅ Queue empty, all steps complete");
            return;
        }

        const nextStep = state.pendingSteps[0];
        console.log(`🔄 Processing queued step: ${nextStep}`);

        set((state) => ({
            pendingSteps: state.pendingSteps.slice(1)
        }));

        // Trigger the next step (implementation in hook)
        get().startWorkflow(nextStep);
    },

    // ─── Reset ────────────────────────────────────────────────────────────────

    reset: () => {
        const state = get();
        if (state.ws) {
            state.ws.close();
        }

        set({
            syllabusSessionId: null,
            pyqsSessionId: null,
            paperSessionId: null,
            syllabusStatus: "idle",
            pyqsStatus: "idle",
            paperStatus: "idle",
            currentStep: null,
            currentProgress: 0,
            ws: null,
            isConnected: false,
            logs: [],
            progressUpdates: [],
            syllabusData: null,
            pyqsData: null,
            paperData: null,
            error: null,
            pendingSteps: []
        });
    },

    clearLogs: () => {
        set({ logs: [], progressUpdates: [] });
    }
}));
