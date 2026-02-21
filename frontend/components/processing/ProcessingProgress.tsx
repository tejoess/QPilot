"use client";

/**
 * components/processing/ProcessingProgress.tsx
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Clock, Timer } from "lucide-react";
import { useProcessingStore } from "@/store/processingStore";

export function ProcessingProgress() {
    const progress = useProcessingStore((s) => s.progress);
    const status = useProcessingStore((s) => s.status);

    return (
        <Card className="border-border/60 shadow-md">
            <CardHeader className="pb-3 px-6">
                <div className="flex items-center justify-between">
                    <div className="space-y-1">
                        <CardTitle className="text-base font-semibold">Overall Progress</CardTitle>
                        <CardDescription className="text-xs">
                            {status === "completed" ? "Generation finished." : "Please do not close this window."}
                        </CardDescription>
                    </div>
                    <div className="h-10 w-10 rounded-full border-2 border-primary/20 flex items-center justify-center p-0.5">
                        <div className="h-full w-full rounded-full bg-primary/5 flex items-center justify-center">
                            <span className="text-xs font-bold text-primary">{progress}%</span>
                        </div>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="px-6 pb-6 space-y-4">
                <Progress value={progress} className="h-2" />

                <div className="grid grid-cols-2 gap-4 pt-2">
                    <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/50">
                        <Timer className="h-4 w-4 text-blue-500" />
                        <div className="space-y-0.5">
                            <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-tight">Elapsed</p>
                            <p className="text-xs font-semibold tabular-nums">0:45s</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/50">
                        <Clock className="h-4 w-4 text-amber-500" />
                        <div className="space-y-0.5">
                            <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-tight">Estimated</p>
                            <p className="text-xs font-semibold tabular-nums">1:30s</p>
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
