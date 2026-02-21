"use client";

/**
 * components/qpilot/VerticalProgressBar.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * A specialized vertical progress bar indicating the pipeline status.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useQPilotStore } from "@/store/qpilotStore";
import { cn } from "@/lib/utils";

export function VerticalProgressBar() {
    const { verticalProgress, status } = useQPilotStore();

    return (
        <div className="w-1.5 h-full bg-border/40 rounded-full relative overflow-hidden">
            <div
                className={cn(
                    "absolute top-0 left-0 w-full transition-all duration-1000 ease-in-out rounded-full",
                    status === "failed" ? "bg-destructive" : "bg-primary"
                )}
                style={{ height: `${verticalProgress}%` }}
            />
            {status === "running" && (
                <div
                    className="absolute top-0 left-0 w-full bg-primary/30 animate-pulse"
                    style={{ height: `${verticalProgress}%` }}
                />
            )}
        </div>
    );
}
