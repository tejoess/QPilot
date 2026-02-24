"use client";

/**
 * components/qpilot/PyqAgentCard.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Compact card for the Previous Year Questions Agent.
 * Supports PDF uploads, text paste, and dynamic subprocess tracking.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState, useRef, useEffect, useCallback } from "react";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from "@/components/ui/select";
import {
    History,
    FileUp,
    Type,
    Play,
    Loader2,
    CheckCircle2,
    AlertCircle,
    Wifi
} from "lucide-react";
import { usePyqStore } from "@/store/pyqStore";
import { useQPilotStore } from "@/store/qpilotStore";
import { useWorkflowOrchestrator } from "@/hooks/useWorkflowOrchestrator";
import { cn } from "@/lib/utils";

interface PyqAgentCardProps {
    projectId: string;
}

const YEARS = ["2025", "2024", "2023", "2022", "2021", "2020"];

export function PyqAgentCard({ projectId }: PyqAgentCardProps) {
    const {
        steps,
        fileName,
        textContent,
        year,
        board,
        setFileName,
        setTextContent,
        setYear,
        setBoard,
        updateStep,
        setError,
        error
    } = usePyqStore();

    const {
        agentStatuses,
        setAgentStatus,
        emitMessage,
        setActiveAgentIndex,
        activeAgentIndex,
        triggerNextAgent
    } = useQPilotStore();

    // 🚀 NEW: WebSocket Orchestrator
    const orchestrator = useWorkflowOrchestrator();

    const status = agentStatuses.pyq;

    const [activeTab, setActiveTab] = useState<"pdf" | "text">("pdf");
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // 🚀 NEW: Sync WebSocket progress to local steps
    useEffect(() => {
        if (orchestrator.pyqsStatus === "running") {
            const progress = orchestrator.currentProgress;
            // Map progress to steps (4 steps for PYQ)
            if (progress >= 0 && progress < 25) {
                updateStep(0, "running");
            } else if (progress >= 25 && progress < 50) {
                updateStep(0, "completed");
                updateStep(1, "running");
            } else if (progress >= 50 && progress < 75) {
                updateStep(1, "completed");
                updateStep(2, "running");
            } else if (progress >= 75) {
                updateStep(2, "completed");
                updateStep(3, "running");
                if (progress === 100) {
                    updateStep(3, "completed");
                }
            }
        }
    }, [orchestrator.currentProgress, orchestrator.pyqsStatus, updateStep]);

    // 🚀 NEW: Handle WebSocket logs
    useEffect(() => {
        orchestrator.logs.slice(-3).forEach(log => {
            if (log.level === "info" && log.message.toLowerCase().includes("pyq")) {
                emitMessage("PYQ Agent", "agent", log.message);
            }
        });
    }, [orchestrator.logs, emitMessage]);

    useEffect(() => {
        if (textContent.length > 50 && !fileName) {
            setActiveTab("text");
        }
    }, [textContent, fileName]);

    const handleStart = useCallback(async () => {
        if (status === "running" || status === "completed") return;

        setAgentStatus("pyq", "running");
        setError(null);
        setActiveAgentIndex(1); // PYQ Agent is index 1

        emitMessage("Orchestrator", "orchestrator", "Initializing PYQ retrieval with WebSocket...");
        emitMessage("PYQ Agent", "agent", `Processing historical data from ${year} (${board})...`);

        try {
            // 🚀 NEW: Use WebSocket Orchestrator
            await orchestrator.analyzePyqs({
                file: activeTab === "pdf" ? uploadedFile : undefined,
                text: activeTab === "text" ? textContent : undefined,
                syllabusSessionId: orchestrator.syllabusSessionId || "", // Use syllabus session
            });

            // Success handled by WebSocket completion message
            setAgentStatus("pyq", "completed");
            emitMessage("PYQ Agent", "agent", "✅ Historical analysis complete. Patterns identified.");
            emitMessage("Orchestrator", "orchestrator", "PYQs complete. Calling Blooxanomy Agent...");
            triggerNextAgent();

        } catch (err) {
            const error = err as { message?: string };
            setError(error?.message || "PYQ processing failed.");
            setAgentStatus("pyq", "failed");
            emitMessage("PYQ Agent", "agent", "❌ Encountered error during processing.");
        }
    }, [
        status,
        activeTab,
        uploadedFile,
        textContent,
        year,
        board,
        setAgentStatus,
        setError,
        setActiveAgentIndex,
        emitMessage,
        orchestrator,
        triggerNextAgent
    ]);

    // Auto-trigger when active
    useEffect(() => {
        const hasData = activeTab === "pdf" ? fileName : textContent.length > 50;
        if (hasData && status === "idle" && activeAgentIndex === 1) {
            handleStart();
        }
    }, [fileName, textContent, activeTab, status, activeAgentIndex, handleStart]);

    // 🚀 NEW: Auto-trigger when orchestrator queues PYQs
    useEffect(() => {
        const hasData = activeTab === "pdf" ? uploadedFile : textContent.length > 50;
        // When orchestrator sets PYQs to "running" (via queue), trigger the actual API call
        if (orchestrator.pyqsStatus === "running" && status === "idle" && hasData) {
            console.log("🎯 Orchestrator triggered PYQs - starting API call");
            handleStart();
        }
    }, [orchestrator.pyqsStatus, status, activeTab, uploadedFile, textContent, handleStart]);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            if (file.type !== "application/pdf") {
                setError("Please upload a PDF file.");
                return;
            }
            setFileName(file.name);
            setUploadedFile(file);
            setError(null);
        }
    };

    return (
        <Card className="w-full border-border/60 shadow-md">
            <CardHeader className="pb-3 px-4">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        <div className="p-1.5 rounded-md bg-amber-500/10 text-amber-600">
                            <History className="h-4 w-4" />
                        </div>
                        Previous Year Questions Agent
                        {/* 🚀 NEW: WebSocket Status */}
                        {orchestrator.isConnected && (
                            <Wifi className="h-3 w-3 text-green-500 animate-pulse" />
                        )}
                    </CardTitle>
                    {status === "completed" && (
                        <Badge className="bg-green-500/10 text-green-600 border-green-200 text-[10px] h-5">
                            Synced
                        </Badge>
                    )}
                </div>
            </CardHeader>

            <CardContent className="px-4 pb-4 space-y-4">
                {status === "idle" ? (
                    <div className="space-y-4 animate-in fade-in duration-300">
                        {/* Context Filters */}
                        <div className="grid grid-cols-2 gap-2">
                            <Select value={year} onValueChange={setYear}>
                                <SelectTrigger className="h-8 text-[11px] font-bold">
                                    <SelectValue placeholder="Year" />
                                </SelectTrigger>
                                <SelectContent>
                                    {YEARS.map(y => <SelectItem key={y} value={y} className="text-[11px] font-bold">{y}</SelectItem>)}
                                </SelectContent>
                            </Select>
                            <Input
                                placeholder="Board"
                                className="h-8 text-[11px] font-bold"
                                value={board}
                                onChange={(e) => setBoard(e.target.value)}
                            />
                        </div>

                        {/* Tab Selection */}
                        <div className="flex gap-1 p-1 bg-muted/50 rounded-lg text-muted-foreground">
                            <Button
                                variant={activeTab === "pdf" ? "secondary" : "ghost"}
                                size="sm"
                                className="flex-1 text-[11px] h-7 font-bold"
                                onClick={() => setActiveTab("pdf")}
                            >
                                <FileUp className="h-3 w-3 mr-2" />
                                PDF Upload
                            </Button>
                            <Button
                                variant={activeTab === "text" ? "secondary" : "ghost"}
                                size="sm"
                                className="flex-1 text-[11px] h-7 font-bold"
                                onClick={() => setActiveTab("text")}
                            >
                                <Type className="h-3 w-3 mr-2" />
                                Text Paste
                            </Button>
                        </div>

                        {activeTab === "pdf" ? (
                            <div className="space-y-2">
                                <input
                                    type="file"
                                    accept=".pdf"
                                    className="hidden"
                                    ref={fileInputRef}
                                    onChange={handleFileChange}
                                />
                                <Button
                                    variant="outline"
                                    className="w-full h-16 border-dashed flex flex-col gap-1 hover:bg-amber-500/5 hover:border-amber-500/50"
                                    onClick={() => fileInputRef.current?.click()}
                                >
                                    <FileUp className="h-4 w-4 text-muted-foreground" />
                                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-tight">
                                        {fileName || "PYQ PDF"}
                                    </span>
                                </Button>
                            </div>
                        ) : (
                            <Textarea
                                placeholder="Paste previous year questions here..."
                                className="text-[11px] min-h-[80px] resize-none focus:ring-1"
                                value={textContent}
                                onChange={(e) => setTextContent(e.target.value)}
                            />
                        )}
                    </div>
                ) : (
                    <div className="space-y-4 py-1 animate-in fade-in duration-400">
                        <div className="space-y-2.5">
                            {steps.map((step, idx) => {
                                const isActive = step.status === "running";
                                const isDone = step.status === "completed";
                                const isFail = step.status === "failed";

                                return (
                                    <div key={idx} className="flex items-center gap-3 px-1">
                                        <div className={cn(
                                            "h-1.5 w-1.5 rounded-full transition-all duration-300",
                                            isActive ? "bg-blue-500 animate-pulse ring-4 ring-blue-500/20" : "bg-muted-foreground/30",
                                            isDone ? "bg-green-500" : "",
                                            isFail ? "bg-red-500" : ""
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
                        </div>

                        {/* 🚀 NEW: Inline WebSocket Logs */}
                        {orchestrator.logs.length > 0 && status === "running" && (
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

                {error && (
                    <div className="flex items-center gap-2 text-[10px] font-bold text-destructive bg-destructive/5 p-2 rounded border border-destructive/20 uppercase tracking-tight">
                        <AlertCircle className="h-3 w-3" />
                        {error}
                    </div>
                )}

                <Button
                    className={cn(
                        "w-full h-10 font-black text-[11px] uppercase tracking-[0.15em] transition-all",
                        status === "running" || status === "completed" ? "bg-green-600 hover:bg-green-700 disabled:opacity-100" : "bg-primary"
                    )}
                    onClick={handleStart}
                    disabled={status === "running" || status === "completed"}
                >
                    {status === "running" ? (
                        <>
                            <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />
                            Processing...
                        </>
                    ) : status === "completed" ? (
                        <>
                            <CheckCircle2 className="h-3.5 w-3.5 mr-2" />
                            Completed
                        </>
                    ) : (
                        <>
                            <Play className="h-3 w-3 mr-2" />
                            Process PYQs
                        </>
                    )}
                </Button>
            </CardContent>
        </Card>
    );
}
