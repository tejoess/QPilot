/**
 * hooks/useWorkflowOrchestrator.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * React hook for orchestrating the 3-step question paper generation workflow:
 * 1. Analyze Syllabus
 * 2. Analyze PYQs (auto-triggered after syllabus)
 * 3. Generate Paper (auto-triggered after PYQs or manual trigger)
 * 
 * Features:
 * - Automatic WebSocket connection before each API call
 * - Sequential execution with queuing
 * - Auto-trigger next step on completion
 * - Error handling and retry logic
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useCallback, useEffect } from "react";
import { useOrchestrationStore } from "@/store/orchestrationStore";
import {
    analyzeSyllabus,
    analyzePyqs,
    generateQuestionPaper,
    type AnalyzeSyllabusRequest,
    type AnalyzePyqsRequest,
    type GenerateQuestionPaperRequest,
} from "@/lib/projectApi";

export function useWorkflowOrchestrator() {
    const store = useOrchestrationStore();

    // ─── Step 1: Analyze Syllabus ─────────────────────────────────────────────

    const runSyllabusAnalysis = useCallback(async (
        fileOrText: { file?: File; text?: string }
    ) => {
        try {
            // Generate session ID for WebSocket
            const sessionId = `syllabus-${Date.now()}`;
            
            console.log("🔧 Starting syllabus analysis with session:", sessionId);
            
            // Connect WebSocket BEFORE making API call
            store.connectWebSocket(sessionId);
            store.setSyllabusSession(sessionId);
            store.startWorkflow("syllabus");
            
            // Wait a moment for WebSocket to connect
            await new Promise(resolve => setTimeout(resolve, 500));

            // Make API call
            const response = await analyzeSyllabus({
                file: fileOrText.file,
                text: fileOrText.text,
                sessionId: sessionId,
            });

            console.log("✅ Syllabus analysis complete:", response);

            // Store results
            store.completeStep("syllabus", response.syllabus);
            
            // Check if PYQs step is queued
            if (store.pendingSteps.includes("pyqs")) {
                console.log("🔄 Auto-triggering PYQ analysis...");
                // Don't call processQueue, it will be called by completion message
            }

            return response;
        } catch (error) {
            const message = error instanceof Error ? error.message : "Unknown error";
            console.error("❌ Syllabus analysis failed:", message);
            store.failStep("syllabus", message);
            throw error;
        }
    }, [store]);

    // ─── Step 2: Analyze PYQs ─────────────────────────────────────────────────

    const runPyqsAnalysis = useCallback(async (
        fileOrText: { file?: File; text?: string }
    ) => {
        try {
            const syllabusSessionId = store.syllabusSessionId;
            
            if (!syllabusSessionId) {
                throw new Error("Syllabus must be analyzed first");
            }

            // Generate session ID for WebSocket
            const sessionId = `pyqs-${Date.now()}`;
            
            console.log("🔧 Starting PYQs analysis with session:", sessionId);

            // Disconnect previous WebSocket and connect new one
            store.disconnectWebSocket();
            await new Promise(resolve => setTimeout(resolve, 200));
            
            store.connectWebSocket(sessionId);
            store.setPyqsSession(sessionId);
            store.startWorkflow("pyqs");
            
            // Wait for WebSocket connection
            await new Promise(resolve => setTimeout(resolve, 500));

            // Make API call
            const response = await analyzePyqs({
                syllabusSessionId,
                file: fileOrText.file,
                text: fileOrText.text,
                sessionId: sessionId,
            });

            console.log("✅ PYQs analysis complete:", response);

            // Store results
            store.completeStep("pyqs", response.pyqs);

            // Check if paper generation is queued
            if (store.pendingSteps.includes("paper")) {
                console.log("🔄 Auto-triggering paper generation...");
            }

            return response;
        } catch (error) {
            const message = error instanceof Error ? error.message : "Unknown error";
            console.error("❌ PYQs analysis failed:", message);
            store.failStep("pyqs", message);
            throw error;
        }
    }, [store]);

    // ─── Step 3: Generate Paper ───────────────────────────────────────────────

    const runPaperGeneration = useCallback(async (
        config: Omit<GenerateQuestionPaperRequest, "syllabusSessionId" | "pyqsSessionId" | "sessionId">
    ) => {
        try {
            const syllabusSessionId = store.syllabusSessionId;
            const pyqsSessionId = store.pyqsSessionId;

            if (!syllabusSessionId || !pyqsSessionId) {
                throw new Error("Both syllabus and PYQs must be analyzed first");
            }

            // Generate session ID for WebSocket
            const sessionId = `paper-${Date.now()}`;
            
            console.log("🔧 Starting paper generation with session:", sessionId);

            // Disconnect previous WebSocket and connect new one
            store.disconnectWebSocket();
            await new Promise(resolve => setTimeout(resolve, 200));
            
            store.connectWebSocket(sessionId);
            store.setPaperSession(sessionId);
            store.startWorkflow("paper");
            
            // Wait for WebSocket connection
            await new Promise(resolve => setTimeout(resolve, 500));

            // Make API call
            const response = await generateQuestionPaper({
                syllabusSessionId,
                pyqsSessionId,
                sessionId,
                ...config,
            });

            console.log("✅ Paper generation complete:", response);

            // Store results
            store.completeStep("paper", response.paper);

            return response;
        } catch (error) {
            const message = error instanceof Error ? error.message : "Unknown error";
            console.error("❌ Paper generation failed:", message);
            store.failStep("paper", message);
            throw error;
        }
    }, [store]);

    // ─── Auto-trigger Logic ───────────────────────────────────────────────────

    useEffect(() => {
        // Listen for syllabus completion → trigger PYQs if queued
        if (store.syllabusStatus === "completed" && 
            store.pyqsStatus === "idle" &&
            store.pendingSteps[0] === "pyqs") {
            
            console.log("🎯 Auto-triggering PYQs analysis after syllabus completion");
            store.processQueue();
        }
    }, [store.syllabusStatus, store.pyqsStatus, store.pendingSteps]);

    useEffect(() => {
        // Listen for PYQs completion → trigger paper if queued
        if (store.pyqsStatus === "completed" && 
            store.paperStatus === "idle" &&
            store.pendingSteps[0] === "paper") {
            
            console.log("🎯 Auto-triggering paper generation after PYQs completion");
            store.processQueue();
        }
    }, [store.pyqsStatus, store.paperStatus, store.pendingSteps]);

    // ─── Cleanup ──────────────────────────────────────────────────────────────

    useEffect(() => {
        return () => {
            // Cleanup WebSocket on unmount
            store.disconnectWebSocket();
        };
    }, []);

    // ─── Return Hook API ──────────────────────────────────────────────────────

    return {
        // Execute functions
        analyzeSyllabus: runSyllabusAnalysis,
        analyzePyqs: runPyqsAnalysis,
        generatePaper: runPaperGeneration,

        // Queue management
        queuePyqsAfterSyllabus: () => store.queueStep("pyqs"),
        queuePaperAfterPyqs: () => store.queueStep("paper"),

        // Status
        syllabusStatus: store.syllabusStatus,
        pyqsStatus: store.pyqsStatus,
        paperStatus: store.paperStatus,

        // Progress
        currentStep: store.currentStep,
        currentProgress: store.currentProgress,
        isConnected: store.isConnected,

        // Data
        syllabusData: store.syllabusData,
        pyqsData: store.pyqsData,
        paperData: store.paperData,

        // Messages
        logs: store.logs,
        progressUpdates: store.progressUpdates,

        // Error
        error: store.error,

        // Control
        reset: store.reset,
        clearLogs: store.clearLogs,
        disconnectWebSocket: store.disconnectWebSocket,

        // Session IDs (for display/debugging)
        syllabusSessionId: store.syllabusSessionId,
        pyqsSessionId: store.pyqsSessionId,
        paperSessionId: store.paperSessionId,
    };
}
