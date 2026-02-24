"use client";

/**
 * components/qpilot/TeacherInputAgentCard.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Final input agent. Allows teachers to provide custom instructions.
 * Acts as the master trigger for the full generation lifecycle.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useRef, useEffect } from "react";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
    MessageSquareQuote,
    Sparkles,
    Loader2,
    CheckCircle2,
    AlertCircle,
    Zap,
    Info,
    Wifi
} from "lucide-react";
import { useGenerationStore } from "@/store/generationStore";
import { usePatternStore } from "@/store/patternStore";
import { useBloomStore } from "@/store/bloomStore";
import { useQPilotStore } from "@/store/qpilotStore";
import { useWorkflowOrchestrator } from "@/hooks/useWorkflowOrchestrator";
import { cn } from "@/lib/utils";

interface TeacherInputAgentCardProps {
    projectId: string;
}

export function TeacherInputAgentCard({ projectId }: TeacherInputAgentCardProps) {
    const {
        teacherInput,
        steps,
        setTeacherInput,
        updateStep,
        setError,
        error
    } = useGenerationStore();

    const {
        status: globalStatus,
        setStatus,
        agentStatuses,
        setAgentStatus,
        emitMessage,
        setActiveAgentIndex,
        updateAgent
    } = useQPilotStore();

    // 🚀 NEW: WebSocket Orchestrator
    const orchestrator = useWorkflowOrchestrator();

    const status = agentStatuses.generation;

    const { getTotalAllocated, getTotalQuestions, totalMarks: targetMarks, sections } = usePatternStore();
    const { bloomLevels } = useBloomStore();
    const { getTotalAssigned } = useBloomStore();

    const totalAllocatedMarks = getTotalAllocated();
    const totalQuestions = getTotalQuestions(); // 📌 FIX: Get actual question count from sections
    const totalBloomQuestions = getTotalAssigned();

    // Validations
    const isPatternValid = totalAllocatedMarks === targetMarks;
    const isBloomValid = totalBloomQuestions > 0;

    // 🚀 NEW: Sync WebSocket progress to local steps
    useEffect(() => {
        if (orchestrator.paperStatus === "running") {
            const progress = orchestrator.currentProgress;
            if (progress >= 0 && progress < 33) {
                updateStep(0, "running");
            } else if (progress >= 33 && progress < 66) {
                updateStep(0, "completed");
                updateStep(1, "running");
            } else if (progress >= 66) {
                updateStep(1, "completed");
                updateStep(2, "running");
                if (progress === 100) {
                    updateStep(2, "completed");
                }
            }
        }
    }, [orchestrator.currentProgress, orchestrator.paperStatus, updateStep]);

    // 🚀 NEW: Handle WebSocket logs
    useEffect(() => {
        orchestrator.logs.slice(-3).forEach(log => {
            if (log.level === "info") {
                emitMessage("Generation Agent", "agent", log.message);
            }
        });
    }, [orchestrator.logs, emitMessage]);

    const handleGenerate = async () => {
        if (status === "running" || status === "completed") return;

        if (!orchestrator.syllabusSessionId || !orchestrator.pyqsSessionId) {
            setError("Please complete Syllabus and PYQ analysis first.");
            return;
        }

        if (!isPatternValid || !isBloomValid) {
            setError("Please complete all required agent steps first.");
            return;
        }

        setAgentStatus("generation", "running");
        setError(null);
        setActiveAgentIndex(4);

        // Chat Behavior
        if (teacherInput.trim()) {
            emitMessage("Teacher", "teacher", teacherInput);
        }
        emitMessage("Orchestrator", "orchestrator", "Initiating final generation...");

        try {
            await triggerFinalGeneration({
                projectId,
                teacherInput
            });

            let stepIdx = 0;
            pollingRef.current = setInterval(() => {
                stepIdx++;
                if (stepIdx <= steps.length) {
                    if (stepIdx > 1) updateStep(stepIdx - 2, "completed");
                    updateStep(stepIdx - 1, "running");
                }
                if (stepIdx === steps.length + 1) {
                    updateStep(steps.length - 1, "completed");
                    setAgentStatus("generation", "completed");

                    emitMessage("Generation Agent", "agent", "Generating question paper...");

                    if (pollingRef.current) clearInterval(pollingRef.current);
                }
            }, 1800);

        } catch (err) {
            const error = err as { message?: string };
            setError(error?.message || "Generation trigger failed.");
            setAgentStatus("generation", "failed");
            emitMessage("Teacher Input Agent", "agent", "❌ Pipeline synthesis failed. System state preserved.");
        }
    };

    return (
        <Card className="w-full border-border/60 shadow-lg overflow-hidden">
            <CardHeader className="pb-3 px-4 bg-primary/5">
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <div className="p-1.5 rounded-md bg-primary text-primary-foreground">
                                <MessageSquareQuote className="h-4 w-4" />
                            </div>
                            Teacher Input Agent
                            {/* 🚀 NEW: WebSocket Status */}
                            {orchestrator.isConnected && (
                                <Wifi className="h-3 w-3 text-green-500 animate-pulse" />
                            )}
                        </CardTitle>
                        <CardDescription className="text-[10px] uppercase font-bold tracking-tight text-muted-foreground/60">
                            Custom Instructions & Requirements
                        </CardDescription>
                    </div>
                    {status === "completed" && (
                        <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-200 text-[10px] h-5 font-bold">
                            Ready
                        </Badge>
                    )}
                </div>
            </CardHeader>

            <CardContent className="px-4 pb-5 pt-4 space-y-4">
                <div className="space-y-4 animate-in fade-in duration-300">
                    <div className="space-y-2">
                        <div className="flex items-center gap-2 mb-1">
                            <Info className="h-3 w-3 text-muted-foreground" />
                            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Special Instructions</span>
                        </div>
                        <Textarea
                            placeholder="Focus more on calculus, avoid repetition from PYQs, add internal choice in Section B, or include at least 2 HOTS questions..."
                            disabled={status === "running"}
                            className="text-[11px] min-h-[120px] leading-relaxed resize-y focus:ring-1 bg-muted/10 border-border/40"
                            value={teacherInput}
                            onChange={(e) => setTeacherInput(e.target.value)}
                        />
                        <div className="flex justify-end">
                            <span className="text-[9px] text-muted-foreground font-medium">{teacherInput.length} characters</span>
                        </div>
                    </div>

                    {error && (
                        <div className="p-2.5 bg-destructive/5 rounded-lg border border-destructive/20 flex items-start gap-2 animate-in shake-in">
                            <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                            <p className="text-[10px] font-bold text-destructive leading-tight">{error}</p>
                        </div>
                    )}

                    {/* 🚀 NEW: Running Steps Visualization */}
                    {status === "running" && (
                        <div className="space-y-2.5 p-3 bg-muted/20 rounded-lg border border-border/40 animate-in fade-in">
                            {steps.map((step, idx) => {
                                const isActive = step.status === "running";
                                const isDone = step.status === "completed";

                                return (
                                    <div key={idx} className="flex items-center gap-3 px-1">
                                        <div className={cn(
                                            "h-1.5 w-1.5 rounded-full transition-all duration-300",
                                            isActive ? "bg-blue-500 animate-pulse ring-4 ring-blue-500/20" : "bg-muted-foreground/30",
                                            isDone ? "bg-green-500" : ""
                                        )} />
                                        <span className={cn(
                                            "text-[10px] font-bold uppercase tracking-widest transition-colors",
                                            isActive ? "text-blue-600" : "text-muted-foreground/60",
                                            isDone ? "text-green-600/70" : ""
                                        )}>
                                            {step.label}
                                        </span>
                                        {isActive && <Loader2 className="h-3 w-3 animate-spin text-blue-500 ml-auto" />}
                                    </div>
                                );
                            })}

                            {/* 🚀 NEW: Inline WebSocket Logs */}
                            {orchestrator.logs.length > 0 && (
                                <div className="mt-3 p-2 bg-muted/30 rounded border border-border/40 space-y-1 max-h-[80px] overflow-y-auto">
                                    {orchestrator.logs.slice(-3).map((log, idx) => (
                                        <div key={idx} className={cn(
                                            "text-[9px] font-mono",
                                            log.level === "info" ? "text-cyan-600" : "",
                                            log.level === "warning" ? "text-yellow-600" : "",
                                            log.level === "error" ? "text-red-600" : ""
                                        )}>
                                            {log.message}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    <Separator className="opacity-40" />

                    <div className="space-y-3">
                        <div className="p-3 bg-muted/30 rounded-lg border border-border/40 space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-[10px] font-bold text-muted-foreground uppercase">Pattern Integrity</span>
                                <Badge variant={isPatternValid ? "secondary" : "outline"} className={cn("text-[9px] h-4", isPatternValid ? "bg-emerald-50 text-emerald-600 border-emerald-100" : "text-amber-500 border-amber-100")}>
                                    {isPatternValid ? "Validated" : "Required"}
                                </Badge>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-[10px] font-bold text-muted-foreground uppercase">Bloom Distribution</span>
                                <Badge variant={isBloomValid ? "secondary" : "outline"} className={cn("text-[9px] h-4", isBloomValid ? "bg-emerald-50 text-emerald-600 border-emerald-100" : "text-amber-500 border-amber-100")}>
                                    {isBloomValid ? "Validated" : "Required"}
                                </Badge>
                            </div>
                        </div>

                        <Button
                            onClick={handleGenerate}
                            className={cn(
                                "w-full h-11 font-black text-[12px] uppercase tracking-widest transition-all shadow-xl",
                                status === "completed" || status === "running" ? "bg-green-600 hover:bg-green-700" : "bg-primary hover:bg-primary/90 shadow-primary/20"
                            )}
                            disabled={status === "running"}
                        >
                            {status === "running" ? (
                                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            ) : status === "completed" ? (
                                <CheckCircle2 className="h-4 w-4 mr-2" />
                            ) : (
                                <Zap className="h-4 w-4 mr-2" />
                            )}
                            {status === "running" ? "Initiating AI Synthesis..." : status === "completed" ? "Paper Generated" : "Generate Question Paper"}
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
