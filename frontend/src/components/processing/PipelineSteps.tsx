"use client";

/**
 * components/processing/PipelineSteps.tsx
 */

import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useProcessingStore, type PipelineStep, type StepStatus } from "@/store/processingStore";

const STATUS_CONFIG: Record<StepStatus, { icon: any; color: string; label: string }> = {
    pending: { icon: CircleDashed, color: "text-muted-foreground", label: "Pending" },
    running: { icon: Loader2, color: "text-primary animate-spin", label: "Processing" },
    completed: { icon: CheckCircle2, color: "text-green-500", label: "Completed" },
    failed: { icon: XCircle, color: "text-destructive", label: "Failed" },
};

export function PipelineSteps() {
    const steps = useProcessingStore((s) => s.steps);

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {steps.map((step) => {
                const config = STATUS_CONFIG[step.status];
                const Icon = config.icon;

                return (
                    <Card key={step.id} className={`border-border/60 transition-all duration-300 ${step.status === 'running' ? 'ring-1 ring-primary/50' : ''}`}>
                        <CardContent className="p-4 flex items-center justify-between">
                            <div className="flex items-center gap-3 min-w-0">
                                <div className={`flex-shrink-0 ${config.color}`}>
                                    <Icon className="h-5 w-5" />
                                </div>
                                <div className="min-w-0">
                                    <p className="text-sm font-semibold truncate leading-tight">{step.name}</p>
                                    <p className="text-[10px] text-muted-foreground truncate">{step.description}</p>
                                </div>
                            </div>
                            <Badge variant={step.status === 'completed' ? 'secondary' : 'outline'} className="text-[10px] ml-2">
                                {config.label}
                            </Badge>
                        </CardContent>
                    </Card>
                );
            })}
        </div>
    );
}
