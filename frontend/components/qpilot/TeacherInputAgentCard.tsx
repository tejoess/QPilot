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
    Info
} from "lucide-react";
import { useGenerationStore } from "@/store/generationStore";
import { usePatternStore } from "@/store/patternStore";
import { useBloomStore } from "@/store/bloomStore";
import { useQPilotStore } from "@/store/qpilotStore";
import { triggerFinalGeneration } from "@/lib/projectApi";
import { cn } from "@/lib/utils";

interface TeacherInputAgentCardProps {
    projectId: string;
}

export function TeacherInputAgentCard({ projectId }: TeacherInputAgentCardProps) {
    const {
        teacherInput,
        status,
        steps,
        setTeacherInput,
        setStatus,
        updateStep,
        startGeneration,
        setError,
        error
    } = useGenerationStore();

    const { getTotalAllocated, totalMarks: targetMarks } = usePatternStore();
    const { getTotalAssigned } = useBloomStore();
    const { updateAgent, setActiveAgentIndex } = useQPilotStore();

    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
        };
    }, []);

    const totalAllocatedMarks = getTotalAllocated();
    const totalBloomQuestions = getTotalAssigned();

    // Validations
    const isPatternValid = totalAllocatedMarks === targetMarks;
    const isBloomValid = totalBloomQuestions > 0;

    const handleGenerate = async () => {
        // 1. Structural Validations
        if (!isPatternValid) {
            setError(`Pattern error: Allocated ${totalAllocatedMarks}/${targetMarks} marks. Please complete the Paper Pattern Agent.`);
            return;
        }
        if (!isBloomValid) {
            setError("Bloom's error: No questions distributed. Please complete the Blooxanomy Agent.");
            return;
        }

        startGeneration();

        try {
            // Trigger API
            await triggerFinalGeneration({
                projectId,
                teacherInput
            });

            // Update vertical pipeline: Move to active status
            // Assuming Teacher Input is index 4 in the 7-agent pipeline
            setActiveAgentIndex(4);
            updateAgent(4, { status: "running", progress: 10 });

            // Simulate the 7-stage subprocess within the card
            let stepIdx = 0;
            pollingRef.current = setInterval(() => {
                stepIdx++;

                if (stepIdx <= steps.length) {
                    if (stepIdx > 1) updateStep(stepIdx - 2, "completed");
                    updateStep(stepIdx - 1, "running");

                    // Sync with the master vertical progress
                    // Map these 7 sub-steps to the Gen Questions (Index 4), Verifier (Index 5), and PDF (Index 6) agents?
                    // For now, just progress the Teacher Input agent itself and then move to next
                    const progress = Math.min(Math.floor((stepIdx / steps.length) * 100), 100);
                    updateAgent(4, { progress });
                }

                if (stepIdx === steps.length + 1) {
                    updateStep(steps.length - 1, "completed");
                    setStatus("completed");
                    updateAgent(4, { status: "completed", progress: 100 });

                    // Automatically move the global pipeline to Gen Questions (Index 5)
                    setActiveAgentIndex(5);
                    updateAgent(5, { status: "running", progress: 50 });

                    if (pollingRef.current) clearInterval(pollingRef.current);
                }
            }, 1500);

        } catch (err: any) {
            setError(err?.message || "Generation trigger failed.");
            setStatus("failed");
        }
    };

    return (
        <Card className="border-border/60 shadow-lg overflow-hidden">
            <CardHeader className="pb-3 px-4 bg-primary/5">
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <div className="p-1.5 rounded-md bg-primary text-primary-foreground">
                                <MessageSquareQuote className="h-4 w-4" />
                            </div>
                            Teacher Input Agent
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
                {status !== "running" && status !== "completed" ? (
                    <div className="space-y-4 animate-in fade-in duration-300">
                        <div className="space-y-2">
                            <div className="flex items-center gap-2 mb-1">
                                <Info className="h-3 w-3 text-muted-foreground" />
                                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Special Instructions</span>
                            </div>
                            <Textarea
                                placeholder="Focus more on calculus, avoid repetition from PYQs, add internal choice in Section B, or include at least 2 HOTS questions..."
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
                                className="w-full h-11 bg-primary hover:bg-primary/90 text-primary-foreground font-black text-[12px] uppercase tracking-widest shadow-xl shadow-primary/20 transition-all active:scale-95"
                            >
                                <Zap className="h-4 w-4 mr-2" />
                                Generate Question Paper
                            </Button>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-5 py-2 animate-in slide-in-from-bottom-3 duration-500">
                        {/* Subprocess Progress */}
                        <div className="space-y-4">
                            {steps.map((step, idx) => {
                                const isActive = step.status === "running";
                                const isDone = step.status === "completed";

                                return (
                                    <div key={idx} className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className={cn(
                                                "h-2 w-2 rounded-full transition-all duration-300",
                                                isActive ? "bg-primary animate-pulse scale-150 shadow-[0_0_12px_var(--primary)]" : "bg-border",
                                                isDone ? "bg-emerald-500" : ""
                                            )} />
                                            <span className={cn(
                                                "text-[11px] font-black tracking-tight uppercase",
                                                isActive ? "text-foreground" : "text-muted-foreground/50",
                                                isDone ? "text-emerald-700/40" : ""
                                            )}>
                                                {step.label}
                                            </span>
                                        </div>
                                        {isActive && <Loader2 className="h-3 w-3 animate-spin text-primary" />}
                                        {isDone && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />}
                                    </div>
                                );
                            })}
                        </div>

                        {status === "completed" && (
                            <div className="p-4 bg-emerald-500/5 rounded-xl border border-emerald-200/50 flex flex-col gap-2 animate-in zoom-in-95">
                                <div className="flex items-center gap-2">
                                    <Sparkles className="h-4 w-4 text-emerald-600" />
                                    <span className="text-[11px] font-black text-emerald-700 uppercase">Generation Complete</span>
                                </div>
                                <p className="text-[10px] font-medium text-emerald-700 leading-normal">
                                    Artificial Intelligence has synthesized the question paper based on your unique constraints. Review the output in the right panel.
                                </p>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
