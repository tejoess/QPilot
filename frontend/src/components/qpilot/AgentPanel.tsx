"use client";

/**
 * components/qpilot/AgentPanel.tsx
 */

import { useQPilotStore, type AgentStatus } from "@/store/qpilotStore";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { VerticalProgressBar } from "@/components/qpilot/VerticalProgressBar";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";
import { SyllabusAgentCard } from "./SyllabusAgentCard";
import { PyqAgentCard } from "./PyqAgentCard";
import { BlooxanomyAgentCard } from "./BlooxanomyAgentCard";
import { PaperPatternAgentCard } from "./PaperPatternAgentCard";
import { TeacherInputAgentCard } from "./TeacherInputAgentCard";
import { AutoFillButton } from "./AutoFillButton";
import { useParams } from "next/navigation";
import { usePatternStore } from "@/store/patternStore";
import { useQPilotConfigStore } from "@/store/qpilotConfigStore";
import { useEffect } from "react";

const STATUS_CONFIG: Record<AgentStatus, { icon: LucideIcon; color: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
    idle: { icon: CircleDashed, color: "text-muted-foreground", variant: "outline" },
    running: { icon: Loader2, color: "text-primary animate-spin", variant: "default" },
    completed: { icon: CheckCircle2, color: "text-green-500", variant: "secondary" },
    failed: { icon: XCircle, color: "text-destructive", variant: "destructive" },
};

export function AgentPanel() {
    const { agents, activeAgentIndex } = useQPilotStore();
    const { projectId } = useParams<{ projectId: string }>();
    const { metadata } = useQPilotConfigStore();
    const { setTotalMarks } = usePatternStore();

    // Sync marks from metadata to pattern store
    useEffect(() => {
        if (metadata.totalMarks) {
            setTotalMarks(metadata.totalMarks);
        }
    }, [metadata.totalMarks, setTotalMarks]);

    return (
        <div className="flex h-full overflow-hidden">
            {/* 1. Far Left Vertical Process Bar */}
            <div className="h-full pt-4 px-4 border-r border-border/20 bg-muted/5">
                <VerticalProgressBar />
            </div>

            {/* 2. Agents Cards List & Chat Panel */}
            <div className="flex-1 flex flex-col min-w-0 h-full">
                {/* Agent List - Scrollable */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                    <AutoFillButton />
                    {agents.map((agent, index) => {
                        const isActive = activeAgentIndex === index;

                        // Specialized Interactive Cards
                        if (agent.id === "syllabus-fetch") {
                            return <SyllabusAgentCard key={agent.id} projectId={projectId} />;
                        }
                        if (agent.id === "pyq-fetch") {
                            return <PyqAgentCard key={agent.id} projectId={projectId} />;
                        }
                        if (agent.id === "blueprint-build") {
                            return <BlooxanomyAgentCard key={agent.id} projectId={projectId} />;
                        }
                        if (agent.id === "blueprint-verify") {
                            return <PaperPatternAgentCard key={agent.id} projectId={projectId} />;
                        }
                        if (agent.id === "teacher-input") {
                            return <TeacherInputAgentCard key={agent.id} projectId={projectId} />;
                        }

                        const config = STATUS_CONFIG[agent.status];
                        const Icon = config.icon;

                        return (
                            <Card
                                key={agent.id}
                                className={cn(
                                    "border-border/40 transition-all duration-300 shadow-none w-full",
                                    isActive ? "ring-1 ring-primary/40 bg-primary/5" : "bg-card/50"
                                )}
                                aria-current={isActive ? "step" : undefined}
                            >
                                <CardContent className="p-4 space-y-3">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <Icon className={cn("h-4 w-4", config.color)} />
                                            <span className="text-sm font-bold text-foreground">{agent.name}</span>
                                        </div>
                                        <Badge variant={config.variant} className="text-[10px] uppercase font-bold tracking-tight px-1.5 h-4">
                                            {agent.status}
                                        </Badge>
                                    </div>

                                    <p className="text-xs text-muted-foreground leading-snug">
                                        {agent.description}
                                    </p>

                                    <div className="space-y-1.5 pt-1">
                                        <div className="flex justify-between items-center text-[10px] font-medium">
                                            <span className="text-muted-foreground">Process Completion</span>
                                            <span className="text-foreground">{agent.progress}%</span>
                                        </div>
                                        <Progress value={agent.progress} className="h-1" />
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>

            </div>
        </div>
    );
}
