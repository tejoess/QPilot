"use client";

/**
 * components/qpilot/SyllabusAgentCard.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Compact card for the Syllabus Fetcher Agent.
 * Handles PDF upload, text paste, and subprocess visualization.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState, useRef, useEffect } from "react";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardFooter
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
    FileUp,
    Type,
    Play,
    Loader2,
    CheckCircle2,
    AlertCircle,
    FileText
} from "lucide-react";
import { useSyllabusStore } from "@/store/syllabusStore";
import { extractSyllabus, getSyllabusStatus } from "@/lib/projectApi";
import { cn } from "@/lib/utils";

interface SyllabusAgentCardProps {
    projectId: string;
}

export function SyllabusAgentCard({ projectId }: SyllabusAgentCardProps) {
    const {
        status,
        steps,
        currentStepIndex,
        fileName,
        textContent,
        setStatus,
        setFileName,
        setTextContent,
        updateStep,
        startExtraction,
        setError,
        error
    } = useSyllabusStore();

    const [activeTab, setActiveTab] = useState<"pdf" | "text">("pdf");
    const fileInputRef = useRef<HTMLInputElement>(null);
    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    // Clean up polling on unmount
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
            setError("Please paste some syllabus content.");
            return;
        }

        startExtraction();

        try {
            // Trigger API
            const response = await extractSyllabus({
                projectId,
                sourceType: activeTab,
                content: activeTab === "text" ? textContent : undefined,
            });

            // Start Polling
            let stepCounter = 0;
            pollingRef.current = setInterval(async () => {
                // In real integration, we'd call getSyllabusStatus(response.jobId)
                // Here we simulate the progression locally for the demonstration
                stepCounter++;

                if (stepCounter <= steps.length) {
                    // Mark previous as completed
                    if (stepCounter > 1) {
                        updateStep(stepCounter - 2, "completed");
                    }
                    // Mark current as running
                    if (stepCounter < steps.length + 1) {
                        updateStep(stepCounter - 1, "running");
                    }
                }

                if (stepCounter === steps.length + 1) {
                    updateStep(steps.length - 1, "completed");
                    setStatus("completed");
                    if (pollingRef.current) clearInterval(pollingRef.current);
                }
            }, 2000);

        } catch (err: any) {
            setError(err?.message || "Extraction failed.");
            setStatus("failed");
        }
    };

    return (
        <Card className="max-w-md border-border/60 shadow-md">
            <CardHeader className="pb-3 px-4">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        <div className="p-1.5 rounded-md bg-primary/10 text-primary">
                            <FileText className="h-4 w-4" />
                        </div>
                        Syllabus Fetcher Agent
                    </CardTitle>
                    {status === "completed" && (
                        <Badge className="bg-green-500/10 text-green-600 border-green-200 text-[10px] h-5">
                            Success
                        </Badge>
                    )}
                </div>
            </CardHeader>

            <CardContent className="px-4 pb-4 space-y-4">
                {status === "idle" ? (
                    <div className="space-y-4 animate-in fade-in duration-300">
                        {/* Input Selection */}
                        <div className="flex gap-1 p-1 bg-muted/50 rounded-lg">
                            <Button
                                variant={activeTab === "pdf" ? "secondary" : "ghost"}
                                size="sm"
                                className="flex-1 text-xs h-8"
                                onClick={() => setActiveTab("pdf")}
                            >
                                <FileUp className="h-3.5 w-3.5 mr-2" />
                                PDF Upload
                            </Button>
                            <Button
                                variant={activeTab === "text" ? "secondary" : "ghost"}
                                size="sm"
                                className="flex-1 text-xs h-8"
                                onClick={() => setActiveTab("text")}
                            >
                                <Type className="h-3.5 w-3.5 mr-2" />
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
                                    className="w-full h-20 border-dashed flex flex-col gap-2 hover:bg-primary/5 hover:border-primary/50"
                                    onClick={() => fileInputRef.current?.click()}
                                >
                                    <FileUp className="h-5 w-5 text-muted-foreground" />
                                    <span className="text-xs font-medium text-muted-foreground">
                                        {fileName || "Click to upload Syllabus PDF"}
                                    </span>
                                </Button>
                            </div>
                        ) : (
                            <Textarea
                                placeholder="Paste syllabus content here..."
                                className="text-xs min-h-[100px] resize-none"
                                value={textContent}
                                onChange={(e) => setTextContent(e.target.value)}
                            />
                        )}

                        {error && (
                            <div className="flex items-center gap-2 text-xs text-destructive bg-destructive/5 p-2 rounded border border-destructive/20">
                                <AlertCircle className="h-3.5 w-3.5" />
                                {error}
                            </div>
                        )}

                        <Button className="w-full h-9 font-bold tracking-wide" onClick={handleStart}>
                            <Play className="h-3.5 w-3.5 mr-2" />
                            Start Extraction
                        </Button>
                    </div>
                ) : (
                    <div className="space-y-5 py-2 animate-in slide-in-from-bottom-2 duration-400">
                        {/* Subprocess Steps */}
                        <div className="space-y-3">
                            {steps.map((step, idx) => {
                                const isActive = step.status === "running";
                                const isDone = step.status === "completed";
                                const isFail = step.status === "failed";

                                return (
                                    <div key={idx} className="flex items-center justify-between group">
                                        <div className="flex items-center gap-3">
                                            <div className={cn(
                                                "h-2 w-2 rounded-full transition-all duration-300",
                                                isActive ? "bg-primary animate-pulse scale-125 shadow-[0_0_8px_var(--primary)]" : "bg-border",
                                                isDone ? "bg-green-500" : "",
                                                isFail ? "bg-destructive" : ""
                                            )} />
                                            <span className={cn(
                                                "text-xs font-medium transition-colors",
                                                isActive ? "text-foreground" : "text-muted-foreground",
                                                isDone ? "text-muted-foreground/60" : ""
                                            )}>
                                                {step.label}
                                            </span>
                                        </div>
                                        {isActive && <Loader2 className="h-3 w-3 animate-spin text-primary" />}
                                        {isDone && <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />}
                                    </div>
                                );
                            })}
                        </div>

                        {status === "completed" && (
                            <div className="p-3 bg-green-500/5 rounded-lg border border-green-200/50 flex items-center gap-3 animate-in zoom-in-95">
                                <CheckCircle2 className="h-4 w-4 text-green-600" />
                                <p className="text-[11px] font-medium text-green-700">
                                    Syllabus extracted and mapped to project successfully.
                                </p>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
