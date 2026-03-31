/**
 * hooks/useGenerationFlow.ts
 *
 * Single hook that fires all 3 backend APIs sequentially:
 *   1. POST /analyze-syllabus
 *   2. POST /analyze-pyqs
 *   3. POST /generate-paper
 *
 * Each call opens its own WebSocket connection first so logs stream in real time.
 * Exposes `phase`, `logs`, `progress`, `paperData`, and `runFullGeneration()`.
 */

import { useCallback, useEffect } from "react";
import { useOrchestrationStore } from "@/store/orchestrationStore";
import { analyzeSyllabus, analyzePyqs, generateQuestionPaper } from "@/lib/projectApi";
import type { BloomLevels } from "@/store/bloomStore";
import type { PatternSection } from "@/store/patternStore";

export type GenerationPhase =
    | "idle"
    | "syllabus"
    | "pyqs"
    | "generating"
    | "done"
    | "error";

export interface GenerationConfig {
    // Syllabus input — exactly one of file/text required
    syllabusFile?: File;
    syllabusText?: string;
    // PYQ input — exactly one of file/text required
    pyqsFile?: File;
    pyqsText?: string;
    // Paper config
    bloomLevels: BloomLevels;
    sections: PatternSection[];
    totalMarks: number;
    totalQuestions: number;
    teacherInput?: string;
    userId?: string;
    projectId?: string;
    // Metadata
    title?: string;
    subject?: string;
    grade?: string;
    duration?: string;
}

// Derive phase from the three step statuses
function derivePhase(
    syllabusStatus: string,
    pyqsStatus: string,
    paperStatus: string
): GenerationPhase {
    if (
        syllabusStatus === "failed" ||
        pyqsStatus === "failed" ||
        paperStatus === "failed"
    )
        return "error";
    if (paperStatus === "completed") return "done";
    if (paperStatus === "running") return "generating";
    if (pyqsStatus === "running") return "pyqs";
    if (syllabusStatus === "running") return "syllabus";
    return "idle";
}

export function useGenerationFlow() {
    const store = useOrchestrationStore();

    const phase = derivePhase(
        store.syllabusStatus,
        store.pyqsStatus,
        store.paperStatus
    );

    // Clean up WebSocket on unmount
    useEffect(() => {
        return () => store.disconnectWebSocket();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const runFullGeneration = useCallback(
        async (config: GenerationConfig) => {
            store.reset();
            store.addLog({
                type: "log",
                timestamp: new Date().toISOString(),
                level: "info",
                message: "Generation started. Initializing agents...",
            });

            // ── Step 1: Analyze Syllabus ──────────────────────────────────────
            const sessionId = `qpilot-${Date.now()}`;
            store.setSyllabusSession(sessionId);
            store.setPyqsSession(sessionId);
            store.setPaperSession(sessionId);
            store.setSyllabusStatus("running");
            store.connectWebSocket(sessionId);
            store.addProgress({
                type: "progress",
                timestamp: new Date().toISOString(),
                step: "syllabus_fetch",
                status: "running",
                progress: 5,
                details: "Connecting to processing engine...",
            });

            // Give WebSocket time to connect
            await new Promise((r) => setTimeout(r, 400));

            let syllabusId: string;
            try {
                const syllabusRes = await analyzeSyllabus({
                    file: config.syllabusFile,
                    text_content: config.syllabusText,
                    sessionId: sessionId,
                    userId: config.userId,
                    projectId: config.projectId,
                    title: config.title,
                    subject: config.subject,
                    grade: config.grade,
                    totalMarks: config.totalMarks,
                    duration: config.duration,
                });
                syllabusId = syllabusRes.session_id;
                store.setSyllabusData(syllabusRes.syllabus);
                store.setSyllabusStatus("completed");
            } catch (err) {
                const msg = err instanceof Error ? err.message : "Syllabus analysis failed";
                store.setError(msg);
                store.setSyllabusStatus("failed");
                return;
            }

            // ── Step 2: Analyze PYQs ─────────────────────────────────────────
            store.setPyqsStatus("running");
            store.addProgress({
                type: "progress",
                timestamp: new Date().toISOString(),
                step: "pyqs_fetch",
                status: "running",
                progress: 35,
                details: "Moving to previous-year paper analysis...",
            });

            let pyqsId: string;
            try {
                const pyqsRes = await analyzePyqs({
                    syllabusSessionId: syllabusId!,
                    file: config.pyqsFile,
                    text_content: config.pyqsText,
                    sessionId: sessionId,
                    userId: config.userId,
                    projectId: config.projectId,
                });
                pyqsId = pyqsRes.session_id;
                store.setPyqsData(pyqsRes.pyqs);
                store.setPyqsStatus("completed");
            } catch (err) {
                const msg = err instanceof Error ? err.message : "PYQ analysis failed";
                store.setError(msg);
                store.setPyqsStatus("failed");
                return;
            }

            // ── Step 3: Generate Paper ────────────────────────────────────────
            store.setPaperStatus("running");
            store.addProgress({
                type: "progress",
                timestamp: new Date().toISOString(),
                step: "question_select",
                status: "running",
                progress: 70,
                details: "Generating and validating final question paper...",
            });

            try {
                const paperPattern =
                    config.sections.length > 0
                        ? {
                              sections: config.sections.map((s) => ({
                                  name: s.name,
                                  type: s.type,
                                  numQuestions: s.numQuestions,
                                  marksPerQuestion: s.marksPerQuestion,
                              })),
                          }
                        : undefined;

                const paperRes = await generateQuestionPaper({
                    syllabusSessionId: syllabusId,
                    pyqsSessionId: pyqsId,
                    sessionId: sessionId,
                    totalMarks: config.totalMarks,
                    totalQuestions: config.totalQuestions,
                    bloomLevels: config.bloomLevels,
                    paperPattern,
                    teacherInput: config.teacherInput,
                    userId: config.userId,
                    projectId: config.projectId,
                });
                store.setPaperData(paperRes.paper);
                store.setPaperStatus("completed");
            } catch (err) {
                const msg = err instanceof Error ? err.message : "Paper generation failed";
                store.setError(msg);
                store.setPaperStatus("failed");
            }
        },
        [store]
    );

    return {
        phase,
        logs: store.logs,
        progressUpdates: store.progressUpdates,
        progress: store.currentProgress,
        isConnected: store.isConnected,
        paperData: store.paperData,
        error: store.error,
        syllabusSessionId: store.syllabusSessionId,
        pyqsSessionId: store.pyqsSessionId,
        paperSessionId: store.paperSessionId,
        runFullGeneration,
        reset: store.reset,
    };
}
