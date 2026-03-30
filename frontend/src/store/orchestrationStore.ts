/**
 * store/orchestrationStore.ts
 * Manages session IDs, step statuses, WebSocket, logs, and paper data.
 */

import { create } from "zustand";

export type StepStatus = "idle" | "running" | "completed" | "failed";

export interface LogMessage {
    type: "log";
    timestamp: string;
    level: "info" | "warning" | "error";
    message: string;
}

export interface ProgressMessage {
    type: "progress";
    timestamp: string;
    step: string;
    status: string;
    progress: number;
    details: string;
}

export type WebSocketMessage =
    | LogMessage
    | ProgressMessage
    | { type: "completion"; timestamp: string; success: boolean; data: Record<string, any> };

interface OrchestrationState {
    // Session IDs
    syllabusSessionId: string | null;
    pyqsSessionId: string | null;
    paperSessionId: string | null;

    // Step statuses
    syllabusStatus: StepStatus;
    pyqsStatus: StepStatus;
    paperStatus: StepStatus;

    // Real-time progress (0â€“100)
    currentProgress: number;

    // WebSocket
    ws: WebSocket | null;
    isConnected: boolean;

    // Streaming messages
    logs: LogMessage[];
    progressUpdates: ProgressMessage[];

    // Result data
    syllabusData: any | null;
    pyqsData: any | null;
    paperData: any | null;

    error: string | null;

    // Actions
    setSyllabusSession: (id: string) => void;
    setPyqsSession: (id: string) => void;
    setPaperSession: (id: string) => void;

    setSyllabusStatus: (s: StepStatus) => void;
    setPyqsStatus: (s: StepStatus) => void;
    setPaperStatus: (s: StepStatus) => void;

    connectWebSocket: (sessionId: string) => void;
    disconnectWebSocket: () => void;
    addLog: (log: LogMessage) => void;
    addProgress: (msg: ProgressMessage) => void;

    setSyllabusData: (data: any) => void;
    setPyqsData: (data: any) => void;
    setPaperData: (data: any) => void;

    setError: (err: string | null) => void;
    clearLogs: () => void;
    reset: () => void;
}

export const useOrchestrationStore = create<OrchestrationState>((set, get) => ({
    syllabusSessionId: null,
    pyqsSessionId: null,
    paperSessionId: null,

    syllabusStatus: "idle",
    pyqsStatus: "idle",
    paperStatus: "idle",

    currentProgress: 0,

    ws: null,
    isConnected: false,

    logs: [],
    progressUpdates: [],

    syllabusData: null,
    pyqsData: null,
    paperData: null,

    error: null,

    setSyllabusSession: (id) => set({ syllabusSessionId: id }),
    setPyqsSession: (id) => set({ pyqsSessionId: id }),
    setPaperSession: (id) => set({ paperSessionId: id }),

    setSyllabusStatus: (s) => set({ syllabusStatus: s }),
    setPyqsStatus: (s) => set({ pyqsStatus: s }),
    setPaperStatus: (s) => set({ paperStatus: s }),

    connectWebSocket: (sessionId) => {
        const { ws } = get();
        if (ws) ws.close();

        const connect = () => {
            const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
            const wsProtocol = baseUrl.startsWith("https") ? "wss" : "ws";
            const hostString = baseUrl.replace(/^https?:\/\//, "");
            const socket = new WebSocket(`${wsProtocol}://${hostString}/ws/${sessionId}`);

            socket.onopen = () => set({ ws: socket, isConnected: true });

            socket.onmessage = (event) => {
                try {
                    const msg: WebSocketMessage = JSON.parse(event.data);
                    if (msg.type === "log") {
                        get().addLog(msg as LogMessage);
                    } else if (msg.type === "progress") {
                        get().addProgress(msg as ProgressMessage);
                        set({ currentProgress: (msg as ProgressMessage).progress });
                    }
                } catch {
                    // ignore malformed messages
                }
            };

            socket.onerror = () => set({ isConnected: false });
            socket.onclose = () => {
                set({ ws: null, isConnected: false });
                
                // If we aren't done, try to auto-reconnect
                const state = get();
                if (state.paperStatus === "running" || state.pyqsStatus === "running" || state.syllabusStatus === "running") {
                    setTimeout(() => {
                        if (get().paperStatus !== "idle" && get().paperStatus !== "completed") {
                            connect();
                        }
                    }, 2000);
                }
            };

            set({ ws: socket });
        };

        connect();
    },

    disconnectWebSocket: () => {
        const { ws } = get();
        if (ws) {
            ws.onclose = null; // Prevent reconnect logic from firing
            ws.close();
        }
        set({ ws: null, isConnected: false });
    },

    addLog: (log) =>
        set((s) => ({ logs: [...s.logs, log].slice(-200) })),

    addProgress: (msg) =>
        set((s) => ({ progressUpdates: [...s.progressUpdates, msg].slice(-50) })),

    setSyllabusData: (data) => set({ syllabusData: data }),
    setPyqsData: (data) => set({ pyqsData: data }),
    setPaperData: (data) => set({ paperData: data }),

    setError: (err) => set({ error: err }),

    clearLogs: () => set({ logs: [], progressUpdates: [] }),

    reset: () => {
        get().disconnectWebSocket();
        set({
            syllabusSessionId: null,
            pyqsSessionId: null,
            paperSessionId: null,
            syllabusStatus: "idle",
            pyqsStatus: "idle",
            paperStatus: "idle",
            currentProgress: 0,
            logs: [],
            progressUpdates: [],
            syllabusData: null,
            pyqsData: null,
            paperData: null,
            error: null,
        });
    },
}));



