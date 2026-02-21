/**
 * hooks/useProcessing.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Hook to manage the interaction between the generation API and WebSocket logs.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useRef, useCallback } from "react";
import { useProcessingStore } from "@/store/processingStore";
import { generatePaper } from "@/lib/projectApi";
import type { PaperGenerationRequest } from "@/types/api";

export function useProcessing(projectId: string, requestData: PaperGenerationRequest | null) {
    const {
        startProcessing,
        updateStep,
        addLog,
        setProgress,
        setResult,
        setError,
        status
    } = useProcessingStore();

    const wsRef = useRef<WebSocket | null>(null);

    const connectWebSocket = useCallback((sessionId: string) => {
        const wsUrl = `${process.env.NEXT_PUBLIC_WS_BASE_URL}/ws/${sessionId}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log("WebSocket connected for session:", sessionId);
        };

        ws.onmessage = (event) => {
            const data = event.data as string;
            addLog(data);

            // Parse step updates if they match the backend pattern: "Step X: name"
            const stepMatch = data.match(/Step (\d+):/i);
            if (stepMatch) {
                const stepNum = stepMatch[1];
                // Mark previous steps as completed
                for (let i = 1; i < parseInt(stepNum); i++) {
                    updateStep(i.toString(), "completed");
                }
                // Mark current step as running
                updateStep(stepNum, "running");

                // Update progress based on step number (9 steps total)
                const progress = Math.round((parseInt(stepNum) / 9) * 100);
                setProgress(progress);
            }
        };

        ws.onerror = (err) => {
            console.error("WebSocket error:", err);
        };

        wsRef.current = ws;
        return ws;
    }, [addLog, updateStep, setProgress]);

    const runGeneration = useCallback(async () => {
        if (!requestData || status !== "idle") return;

        startProcessing();

        // session_1 is used in backend main.py example, but we'll use a unique one if we can.
        // However, the current backend main.py hardcodes session_1.
        const sessionId = "session_1";

        const ws = connectWebSocket(sessionId);

        try {
            const response = await generatePaper(requestData);

            if (response.status === "success") {
                // Mark all steps as completed before finishing
                for (let i = 1; i <= 9; i++) {
                    updateStep(i.toString(), "completed");
                }
                setResult(response.file_path);
            } else {
                setError("Generation failed on backend.");
            }
        } catch (err) {
            const error = err as { message?: string };
            setError(error?.message || "Failed to trigger generation.");
        } finally {
            if (ws.readyState === WebSocket.OPEN) {
                // Optional: wait a bit before closing to ensure logs arrive
                setTimeout(() => ws.close(), 1000);
            }
        }
    }, [requestData, status, startProcessing, connectWebSocket, updateStep, setResult, setError]);

    return { runGeneration };
}
