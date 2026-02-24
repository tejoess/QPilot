/**
 * components/processing/WebSocketLogPanel.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Real-time log panel showing WebSocket messages during workflow execution.
 * Displays progress bars, log messages, and completion status.
 * ─────────────────────────────────────────────────────────────────────────────
 */

"use client";

import { useEffect, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Wifi, WifiOff, CheckCircle2, AlertCircle, Info } from "lucide-react";
import { useOrchestrationStore } from "@/store/orchestrationStore";
import { cn } from "@/lib/utils";

export function WebSocketLogPanel() {
    const { isConnected, logs, progressUpdates, currentProgress, currentStep, error } =
        useOrchestrationStore();
    
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs, progressUpdates]);

    // Get latest progress update
    const latestProgress = progressUpdates[progressUpdates.length - 1];

    return (
        <Card className="h-full flex flex-col">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="text-lg">Real-Time Logs</CardTitle>
                        <CardDescription>
                            Live updates from backend pipeline
                        </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                        {isConnected ? (
                            <>
                                <Wifi className="h-4 w-4 text-green-500" />
                                <Badge variant="outline" className="text-green-600 border-green-600">
                                    Connected
                                </Badge>
                            </>
                        ) : (
                            <>
                                <WifiOff className="h-4 w-4 text-muted-foreground" />
                                <Badge variant="outline" className="text-muted-foreground">
                                    Disconnected
                                </Badge>
                            </>
                        )}
                    </div>
                </div>

                {/* Current Progress Bar */}
                {isConnected && currentStep && (
                    <div className="mt-4 space-y-2">
                        <div className="flex items-center justify-between text-sm">
                            <span className="font-medium capitalize">{currentStep}</span>
                            <span className="text-muted-foreground">{currentProgress}%</span>
                        </div>
                        <Progress value={currentProgress} className="h-2" />
                        {latestProgress && (
                            <p className="text-xs text-muted-foreground">
                                {latestProgress.details}
                            </p>
                        )}
                    </div>
                )}

                {/* Error Display */}
                {error && (
                    <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-md flex items-start gap-2">
                        <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
                        <div>
                            <p className="text-sm font-medium text-destructive">Error</p>
                            <p className="text-xs text-destructive/80 mt-1">{error}</p>
                        </div>
                    </div>
                )}
            </CardHeader>

            <CardContent className="flex-1 min-h-0 pb-4">
                <ScrollArea className="h-full pr-4" ref={scrollRef}>
                    <div className="space-y-2">
                        {logs.length === 0 && progressUpdates.length === 0 ? (
                            <div className="text-center py-8 text-muted-foreground">
                                <Info className="h-8 w-8 mx-auto mb-2 opacity-50" />
                                <p className="text-sm">No logs yet</p>
                                <p className="text-xs mt-1">
                                    Logs will appear when workflow starts
                                </p>
                            </div>
                        ) : (
                            <>
                                {/* Render logs and progress updates in chronological order */}
                                {[...logs, ...progressUpdates]
                                    .sort((a, b) => 
                                        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
                                    )
                                    .map((message, index) => (
                                        <LogMessage key={index} message={message} />
                                    ))}
                            </>
                        )}
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    );
}

// ─── Individual Log Message Component ────────────────────────────────────────

interface LogMessageProps {
    message: any; // LogMessage | ProgressMessage
}

function LogMessage({ message }: LogMessageProps) {
    const time = new Date(message.timestamp).toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    });

    if (message.type === "log") {
        return (
            <div className={cn(
                "flex items-start gap-2 p-2 rounded-md text-sm",
                message.level === "error" && "bg-destructive/10 text-destructive",
                message.level === "warning" && "bg-yellow-500/10 text-yellow-700 dark:text-yellow-500",
                message.level === "info" && "bg-muted/50"
            )}>
                <span className="text-xs text-muted-foreground tabular-nums flex-shrink-0 mt-0.5">
                    {time}
                </span>
                {message.level === "error" && (
                    <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                )}
                {message.level === "warning" && (
                    <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                )}
                {message.level === "info" && (
                    <CheckCircle2 className="h-4 w-4 flex-shrink-0 mt-0.5 text-green-500" />
                )}
                <span className="flex-1 font-mono">{message.message}</span>
            </div>
        );
    }

    if (message.type === "progress") {
        return (
            <div className="flex items-start gap-2 p-2 rounded-md bg-blue-500/10 text-sm">
                <span className="text-xs text-muted-foreground tabular-nums flex-shrink-0 mt-0.5">
                    {time}
                </span>
                <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                        <span className="font-medium text-blue-600 dark:text-blue-400">
                            {message.step}
                        </span>
                        <Badge 
                            variant={message.status === "completed" ? "default" : "secondary"}
                            className="text-xs"
                        >
                            {message.progress}%
                        </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{message.details}</p>
                </div>
            </div>
        );
    }

    // Completion message
    if (message.type === "completion") {
        return (
            <div className="flex items-start gap-2 p-3 rounded-md bg-green-500/10 border border-green-500/20 text-sm">
                <CheckCircle2 className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                    <p className="font-medium text-green-600 dark:text-green-400">
                        Workflow Completed
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                        {time} • {message.success ? "Success" : "Failed"}
                    </p>
                </div>
            </div>
        );
    }

    return null;
}
