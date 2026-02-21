"use client";

/**
 * hooks/useQPilotInterface.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Orchestrates the QPilot Live Interface:
 * 1. Triggers generation API
 * 2. Manages WebSocket status updates
 * 3. Updates the QPilot store (agents progress, vertical bar, paper content)
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useRef, useCallback } from "react";
import { useQPilotStore } from "@/store/qpilotStore";
import { generatePaper } from "@/lib/projectApi";
import type { PaperGenerationRequest } from "@/types/api";

export function useQPilotInterface(projectId: string, requestData: PaperGenerationRequest | null) {
    const {
        setStatus,
        updateAgent,
        setActiveAgentIndex,
        addQuestion,
        status,
        agents
    } = useQPilotStore();

    const wsRef = useRef<WebSocket | null>(null);

    const connectWebSocket = useCallback((sessionId: string) => {
        const wsUrl = `${process.env.NEXT_PUBLIC_WS_BASE_URL}/ws/${sessionId}`;
        const ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
            const data = event.data as string;

            // --- PIPELINE STATUS MAPPING ---
            // Pattern: "Step X: Name"
            const stepMatch = data.match(/Step (\d+):/i);
            if (stepMatch) {
                const stepNum = parseInt(stepMatch[1]);

                // Map backend 9-step pipeline to frontend 5-step pipeline
                let mappedIndex = 0;
                if (stepNum === 1 || stepNum === 2) mappedIndex = 0; // Syllabus Agent
                else if (stepNum === 3 || stepNum === 4) mappedIndex = 1; // PYQ Agent
                else if (stepNum === 5) mappedIndex = 2; // Blooxanomy Agent
                else if (stepNum === 6) mappedIndex = 3; // Paper Pattern Agent
                else if (stepNum >= 7) mappedIndex = 4; // Teacher Input Agent

                // Complete previous agents
                for (let i = 0; i < mappedIndex; i++) {
                    updateAgent(i, { status: "completed", progress: 100 });
                }

                // Start current agent
                setActiveAgentIndex(mappedIndex);
                updateAgent(mappedIndex, {
                    status: "running",
                    progress: (stepNum % 2 === 0 && stepNum < 5) ? 80 : 30
                });
            }

            // Progress Simulation within an agent
            if (data.includes("Blueprint Build")) {
                updateAgent(2, { progress: 60 });
            }

            // Incremental content generation (Previously agent 4, now also agent 4 but for gen content)
            if (data.includes("Select Questions")) {
                updateAgent(4, { progress: 80 });
                setTimeout(() => {
                    addQuestion("Section A: Objectives", {
                        number: 1,
                        text: "Identify the primary benefit of multi-agent collaboration in AI workflows.",
                        marks: 1
                    });
                }, 1000);
            }

            if (data.includes("generate final")) {
                updateAgent(4, { progress: 95 }); // Still updating Teacher Input since it's the last trigger card
                addQuestion("Section B: Subjective", {
                    number: 2,
                    text: "Design a fail-safe mechanism for an autonomous grading agent.",
                    marks: 5
                });
            }
        };

        wsRef.current = ws;
        return ws;
    }, [updateAgent, setActiveAgentIndex, addQuestion]);

    const runGeneration = useCallback(async () => {
        if (!requestData || status !== "idle") return;

        setStatus("running");

        // In production, session ID would be project specific
        const sessionId = "session_1";
        const ws = connectWebSocket(sessionId);

        try {
            const response = await generatePaper(requestData);

            if (response.status === "success") {
                // Finalize all agents
                agents.forEach((_, idx) => updateAgent(idx, { status: "completed", progress: 100 }));
                setActiveAgentIndex(agents.length - 1); // Set to last agent
                setStatus("completed");
            } else {
                setStatus("failed");
            }
        } catch (err: any) {
            setStatus("failed");
        } finally {
            if (ws.readyState === WebSocket.OPEN) {
                setTimeout(() => ws.close(), 2000);
            }
        }
    }, [requestData, status, setStatus, connectWebSocket, updateAgent, setActiveAgentIndex, agents]);

    return { runGeneration };
}
