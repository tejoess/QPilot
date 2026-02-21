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
import { useQPilotStore } from "@/store/qpilotStore";
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
        steps,
        setLevel,
        updateStep,
        getTotalAssigned,
        setError,
        error
    } = useBloomStore();

    const {
        agentStatuses,
        setAgentStatus,
        emitMessage,
        setActiveAgentIndex,
        triggerNextAgent
    } = useQPilotStore();

    const status = agentStatuses.bloom;

    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
        };
    }, []);

    const handleApply = async () => {
        if (status === "running" || status === "completed") return;

        const total = getTotalAssigned();
        if (total === 0) {
            setError("Please assign at least one question to a level.");
            return;
        }

        setAgentStatus("bloom", "running");
        setError(null);
        setActiveAgentIndex(2);

        // Minimal chat behavior for manual mode
        emitMessage("Orchestrator", "orchestrator", "Applying Bloom's taxonomy distribution...");

        try {
            await applyBloomDistribution({
                projectId,
                levels: bloomLevels
            });

            let stepIdx = 0;
            pollingRef.current = setInterval(() => {
                stepIdx++;

                if (stepIdx <= steps.length) {
                    if (stepIdx > 1) updateStep(stepIdx - 2, "completed");
                    updateStep(stepIdx - 1, "running");
                    // No verbose subprocess breakdown in chat
                }

                if (stepIdx === steps.length + 1) {
                    updateStep(steps.length - 1, "completed");
                    setAgentStatus("bloom", "completed");

                    emitMessage("Blooxanomy Agent", "agent", "Bloom levels successfully assigned.");
                    triggerNextAgent();

                    if (pollingRef.current) clearInterval(pollingRef.current);
                }
            }, 1500);

        } catch (err) {
            const error = err as { message?: string };
            setError(error?.message || "Bloom's mapping failed.");
            setAgentStatus("bloom", "failed");
            emitMessage("Blooxanomy Agent", "agent", "Mapping interrupted. Semantic constraints violation detected.");
        }
    };

    return (
        <Card className="w-full border-border/60 shadow-md">
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
                <div className="space-y-4 animate-in fade-in duration-300">
                    {/* Input Grid */}
                    <div className="grid grid-cols-2 gap-x-6 gap-y-3 p-3 bg-muted/30 rounded-xl border border-border/40">
                        {BLOOM_LEVELS.map((level) => (
                            <div key={level.id} className="flex items-center justify-between gap-2">
                                <span className="text-[11px] font-semibold text-muted-foreground">{level.label}</span>
                                <Input
                                    type="number"
                                    disabled={status === "running"}
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

                    <Button
                        className={cn(
                            "w-full h-9 font-bold text-xs shadow-lg shadow-primary/10 transition-all",
                            status === "completed" || status === "running" ? "bg-green-600 hover:bg-green-700" : "bg-primary"
                        )}
                        onClick={handleApply}
                        disabled={status === "running"}
                    >
                        {status === "running" ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin mr-2" />
                        ) : status === "completed" ? (
                            <CheckCircle2 className="h-3.5 w-3.5 mr-2" />
                        ) : (
                            <SendHorizontal className="h-3.5 w-3.5 mr-2" />
                        )}
                        {status === "running" ? "Applying..." : status === "completed" ? "Distribution Applied" : "Apply Bloom Distribution"}
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}
