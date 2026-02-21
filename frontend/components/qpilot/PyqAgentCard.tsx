"use client";

/**
 * components/qpilot/PyqAgentCard.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Compact card for the Previous Year Questions Agent.
 * Supports PDF uploads, text paste, and dynamic subprocess tracking.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState, useRef, useEffect } from "react";
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
    AlertCircle
} from "lucide-react";
import { usePyqStore } from "@/store/pyqStore";
import { processPyqs } from "@/lib/projectApi";
import { cn } from "@/lib/utils";

interface PyqAgentCardProps {
    projectId: string;
}

const YEARS = ["2025", "2024", "2023", "2022", "2021", "2020"];

export function PyqAgentCard({ projectId }: PyqAgentCardProps) {
    const {
        status,
        steps,
        fileName,
        textContent,
        year,
        board,
        setStatus,
        setFileName,
        setTextContent,
        setYear,
        setBoard,
        updateStep,
        startProcessing,
        setError,
        error
    } = usePyqStore();

    const [activeTab, setActiveTab] = useState<"pdf" | "text">("pdf");
    const fileInputRef = useRef<HTMLInputElement>(null);
    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
        };
    }, []);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            if (file.type !== "application/pdf") {
                setError("Please upload a PDF file.");
                return;
            }
            setFileName(file.name);
            setError(null);
        }
    };

    const handleStart = async () => {
        if (activeTab === "pdf" && !fileName) {
            setError("Please select a PDF file first.");
            return;
        }
        if (activeTab === "text" && !textContent.trim()) {
            setError("Please paste some questions.");
            return;
        }

        startProcessing();

        try {
            const response = await processPyqs({
                projectId,
                sourceType: activeTab,
                content: activeTab === "text" ? textContent : undefined,
                year,
                board
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
            }, 2000);

        } catch (err: any) {
            setError(err?.message || "PYQ processing failed.");
            setStatus("failed");
        }
    };

    return (
        <Card className="max-w-md border-border/60 shadow-md">
            <CardHeader className="pb-3 px-4">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        <div className="p-1.5 rounded-md bg-amber-500/10 text-amber-600">
                            <History className="h-4 w-4" />
                        </div>
                        Previous Year Questions Agent
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
                                <SelectTrigger className="h-8 text-[11px]">
                                    <SelectValue placeholder="Select Year" />
                                </SelectTrigger>
                                <SelectContent>
                                    {YEARS.map(y => <SelectItem key={y} value={y} className="text-[11px]">{y}</SelectItem>)}
                                </SelectContent>
                            </Select>
                            <Input
                                placeholder="Board (e.g. CBSE)"
                                className="h-8 text-[11px]"
                                value={board}
                                onChange={(e) => setBoard(e.target.value)}
                            />
                        </div>

                        {/* Tab Selection */}
                        <div className="flex gap-1 p-1 bg-muted/50 rounded-lg text-muted-foreground">
                            <Button
                                variant={activeTab === "pdf" ? "secondary" : "ghost"}
                                size="sm"
                                className="flex-1 text-[11px] h-7"
                                onClick={() => setActiveTab("pdf")}
                            >
                                <FileUp className="h-3 w-3 mr-2" />
                                PDF Upload
                            </Button>
                            <Button
                                variant={activeTab === "text" ? "secondary" : "ghost"}
                                size="sm"
                                className="flex-1 text-[11px] h-7"
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
                                    <span className="text-[10px] font-medium text-muted-foreground">
                                        {fileName || "Drop PYQ PDF or click to browse"}
                                    </span>
                                </Button>
                            </div>
                        ) : (
                            <Textarea
                                placeholder="Paste previous year questions here..."
                                className="text-xs min-h-[80px] resize-none"
                                value={textContent}
                                onChange={(e) => setTextContent(e.target.value)}
                            />
                        )}

                        {error && (
                            <div className="flex items-center gap-2 text-[11px] text-destructive bg-destructive/5 p-2 rounded border border-destructive/20">
                                <AlertCircle className="h-3 w-3" />
                                {error}
                            </div>
                        )}

                        <Button className="w-full h-9 font-bold text-xs" onClick={handleStart}>
                            <Play className="h-3 w-3 mr-2" />
                            Process PYQs
                        </Button>
                    </div>
                ) : (
                    <div className="space-y-4 py-1 animate-in slide-in-from-bottom-2 duration-400">
                        {/* Step List */}
                        <div className="space-y-2.5">
                            {steps.map((step, idx) => {
                                const isActive = step.status === "running";
                                const isDone = step.status === "completed";
                                const isFail = step.status === "failed";

                                return (
                                    <div key={idx} className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className={cn(
                                                "h-2 w-2 rounded-full transition-all duration-300",
                                                isActive ? "bg-amber-500 animate-pulse scale-125 shadow-[0_0_8px_rgba(245,158,11,0.5)]" : "bg-border",
                                                isDone ? "bg-amber-500" : "",
                                                isFail ? "bg-destructive" : ""
                                            )} />
                                            <span className={cn(
                                                "text-[11px] font-medium",
                                                isActive ? "text-foreground" : "text-muted-foreground",
                                                isDone ? "text-muted-foreground/60" : ""
                                            )}>
                                                {step.label}
                                            </span>
                                        </div>
                                        {isActive && <Loader2 className="h-3 w-3 animate-spin text-amber-600" />}
                                        {isDone && <CheckCircle2 className="h-3 w-3 text-amber-500" />}
                                    </div>
                                );
                            })}
                        </div>

                        {status === "completed" && (
                            <div className="p-3 bg-amber-500/5 rounded-lg border border-amber-200/50 flex items-center gap-3 animate-in fade-in duration-500">
                                <CheckCircle2 className="h-4 w-4 text-amber-600" />
                                <p className="text-[10px] font-medium text-amber-700 leading-tight">
                                    Questions extracted, categorized and indexed for generation.
                                </p>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
