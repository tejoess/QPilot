"use client";

/**
 * components/qpilot/BlooxanomyAgentCard.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Bloom's Taxonomy Agent interface. Handles cognitive level distribution 
 * and maps questions to educational objectives.
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
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
    BrainCircuit,
    CheckCircle2,
    Loader2,
    AlertCircle,
    BarChart3,
    SendHorizontal
} from "lucide-react";
import { useBloomStore, type BloomLevels } from "@/store/bloomStore";
import { applyBloomDistribution } from "@/lib/projectApi";
import { cn } from "@/lib/utils";

interface BlooxanomyAgentCardProps {
    projectId: string;
}

const BLOOM_LEVELS: { id: keyof BloomLevels; label: string }[] = [
    { id: "remember", label: "Remember" },
    { id: "understand", label: "Understand" },
    { id: "apply", label: "Apply" },
    { id: "analyze", label: "Analyze" },
    { id: "evaluate", label: "Evaluate" },
    { id: "create", label: "Create" },
];

export function BlooxanomyAgentCard({ projectId }: BlooxanomyAgentCardProps) {
    const {
        bloomLevels,
        status,
        steps,
        setStatus,
        setLevel,
        updateStep,
        startBloomProcess,
        getTotalAssigned,
        setError,
        error
    } = useBloomStore();

    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
        };
    }, []);

    const handleApply = async () => {
        const total = getTotalAssigned();
        if (total === 0) {
            setError("Please assign at least one question to a level.");
            return;
        }

        startBloomProcess();

        try {
            const response = await applyBloomDistribution({
                projectId,
                levels: bloomLevels
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
                    setStatus("completed");
                    if (pollingRef.current) clearInterval(pollingRef.current);
                }
            }, 1500);

        } catch (err: any) {
            setError(err?.message || "Bloom's mapping failed.");
            setStatus("failed");
        }
    };

    return (
        <Card className="max-w-md border-border/60 shadow-md">
            <CardHeader className="pb-3 px-4">
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <div className="p-1.5 rounded-md bg-indigo-500/10 text-indigo-600">
                                <BrainCircuit className="h-4 w-4" />
                            </div>
                            Blooxanomy Agent
                        </CardTitle>
                        <CardDescription className="text-[10px] uppercase font-medium">
                            Cognitive Level Mapping
                        </CardDescription>
                    </div>
                    {status === "completed" && (
                        <Badge className="bg-indigo-500/10 text-indigo-600 border-indigo-200 text-[10px] h-5">
                            Mapped
                        </Badge>
                    )}
                </div>
            </CardHeader>

            <CardContent className="px-4 pb-4 space-y-4">
                {status === "idle" ? (
                    <div className="space-y-4 animate-in fade-in duration-300">
                        {/* Input Grid */}
                        <div className="grid grid-cols-2 gap-x-6 gap-y-3 p-3 bg-muted/30 rounded-xl border border-border/40">
                            {BLOOM_LEVELS.map((level) => (
                                <div key={level.id} className="flex items-center justify-between gap-2">
                                    <span className="text-[11px] font-semibold text-muted-foreground">{level.label}</span>
                                    <Input
                                        type="number"
                                        className="h-7 w-12 text-center text-[11px] font-bold p-1 bg-background"
                                        value={bloomLevels[level.id] || ""}
                                        onChange={(e) => setLevel(level.id, parseInt(e.target.value) || 0)}
                                    />
                                </div>
                            ))}
                        </div>

                        {/* Summary Area */}
                        <div className="flex items-center justify-between px-2">
                            <div className="flex items-center gap-2 text-indigo-600">
                                <BarChart3 className="h-4 w-4" />
                                <span className="text-xs font-bold tracking-tight">Total Allocated: {getTotalAssigned()} questions</span>
                            </div>
                            {error && (
                                <div className="flex items-center gap-1.5 text-[10px] text-destructive font-medium animate-in slide-in-from-right-2">
                                    <AlertCircle className="h-3 w-3" />
                                    {error}
                                </div>
                            )}
                        </div>

                        <Separator className="opacity-50" />

                        <Button className="w-full h-9 font-bold text-xs bg-primary hover:bg-primary/90 shadow-lg shadow-primary/10" onClick={handleApply}>
                            <SendHorizontal className="h-3.5 w-3.5 mr-2" />
                            Apply Bloom Distribution
                        </Button>
                    </div>
                ) : (
                    <div className="space-y-4 py-1 animate-in slide-in-from-bottom-2 duration-400">
                        {/* Step List */}
                        <div className="space-y-3">
                            {steps.map((step, idx) => {
                                const isActive = step.status === "running";
                                const isDone = step.status === "completed";
                                const isFail = step.status === "failed";

                                return (
                                    <div key={idx} className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className={cn(
                                                "h-1.5 w-1.5 rounded-full transition-all duration-300",
                                                isActive ? "bg-indigo-500 animate-pulse scale-150 shadow-[0_0_10px_rgba(79,70,229,0.6)]" : "bg-border",
                                                isDone ? "bg-indigo-500" : "",
                                                isFail ? "bg-destructive" : ""
                                            )} />
                                            <span className={cn(
                                                "text-[11px] font-bold tracking-wide",
                                                isActive ? "text-foreground" : "text-muted-foreground/70",
                                                isDone ? "text-muted-foreground/40 line-through decoration-indigo-500/30" : ""
                                            )}>
                                                {step.label}
                                            </span>
                                        </div>
                                        {isActive && <Loader2 className="h-3 w-3 animate-spin text-indigo-600" />}
                                        {isDone && <CheckCircle2 className="h-3.5 w-3.5 text-indigo-500" />}
                                    </div>
                                );
                            })}
                        </div>

                        {status === "completed" && (
                            <div className="p-3 bg-indigo-500/5 rounded-lg border border-indigo-200/50 flex items-start gap-3 animate-in fade-in duration-500">
                                <CheckCircle2 className="h-4 w-4 text-indigo-600 mt-0.5 shrink-0" />
                                <p className="text-[10px] font-medium text-indigo-700 leading-relaxed">
                                    Distribution verified. Questions have been tagged with cognitive levels and secondary objectives mapped.
                                </p>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
