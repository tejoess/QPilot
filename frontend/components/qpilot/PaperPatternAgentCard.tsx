"use client";

/**
 * components/qpilot/PaperPatternAgentCard.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Agent card for defining the paper's structural pattern.
 * Manages section-wise question types, counts, and marks weightage.
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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
    Layers,
    Plus,
    Trash2,
    Play,
    Loader2,
    CheckCircle2,
    AlertCircle,
    Hash,
    Award,
    ChevronRight
} from "lucide-react";
import { usePatternStore } from "@/store/patternStore";
import { applyPaperPattern } from "@/lib/projectApi";
import { cn } from "@/lib/utils";

interface PaperPatternAgentCardProps {
    projectId: string;
}

const QUESTION_TYPES = [
    { value: "mcq", label: "MCQ" },
    { value: "short_answer", label: "Short Answer" },
    { value: "long_answer", label: "Long Answer" },
    { value: "case_study", label: "Case Study" },
];

export function PaperPatternAgentCard({ projectId }: PaperPatternAgentCardProps) {
    const {
        sections,
        totalMarks,
        status,
        steps,
        addSection,
        updateSection,
        deleteSection,
        setStatus,
        updateStep,
        startPatternProcess,
        getTotalAllocated,
        setError,
        error
    } = usePatternStore();

    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
        };
    }, []);

    const totalAllocated = getTotalAllocated();
    const isMatched = totalAllocated === totalMarks;
    const isExceeded = totalAllocated > totalMarks;
    const isUnder = totalAllocated < totalMarks;

    const handleAddSection = () => {
        addSection({
            name: `Section ${String.fromCharCode(65 + sections.length)}`,
            type: "mcq",
            numQuestions: 5,
            marksPerQuestion: 1,
        });
    };

    const handleApply = async () => {
        if (sections.length === 0) {
            setError("Please add at least one section.");
            return;
        }
        if (!isMatched) {
            setError(`Marks mismatch. Target: ${totalMarks}, Allocated: ${totalAllocated}`);
            return;
        }

        startPatternProcess();

        try {
            const response = await applyPaperPattern({
                projectId,
                sections: sections.map(s => ({
                    name: s.name,
                    type: s.type,
                    numQuestions: s.numQuestions,
                    marksPerQuestion: s.marksPerQuestion
                }))
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
            setError(err?.message || "Pattern application failed.");
            setStatus("failed");
        }
    };

    return (
        <Card className="border-border/60 shadow-md">
            <CardHeader className="pb-3 px-4">
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <div className="p-1.5 rounded-md bg-emerald-500/10 text-emerald-600">
                                <Layers className="h-3.5 w-3.5" />
                            </div>
                            Paper Pattern Agent
                        </CardTitle>
                        <CardDescription className="text-[10px] uppercase font-bold tracking-tight text-muted-foreground/60">
                            Weightage Configuration
                        </CardDescription>
                    </div>
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-[10px] font-bold text-emerald-600 hover:bg-emerald-500/10"
                        onClick={handleAddSection}
                    >
                        <Plus className="h-3 w-3 mr-1" />
                        Add Section
                    </Button>
                </div>
            </CardHeader>

            <CardContent className="px-3 pb-4 space-y-4">
                {status === "idle" ? (
                    <div className="space-y-4 animate-in fade-in duration-300">
                        {sections.length === 0 ? (
                            <div className="py-6 text-center border-2 border-dashed border-muted rounded-xl bg-muted/20">
                                <p className="text-[11px] text-muted-foreground font-semibold">No sections added yet.</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {sections.map((section) => (
                                    <div key={section.id} className="p-2.5 bg-muted/30 rounded-lg border border-border/40 space-y-2.5 relative group">
                                        <button
                                            onClick={() => deleteSection(section.id)}
                                            className="absolute top-1.5 right-1.5 p-1 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                                        >
                                            <Trash2 className="h-3 w-3" />
                                        </button>

                                        <div className="flex items-center gap-2">
                                            <Input
                                                value={section.name}
                                                onChange={(e) => updateSection(section.id, { name: e.target.value })}
                                                className="h-6 text-[11px] font-bold bg-background flex-1"
                                            />
                                            <Select value={section.type} onValueChange={(val) => updateSection(section.id, { type: val })}>
                                                <SelectTrigger className="h-6 w-28 text-[11px] bg-background">
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {QUESTION_TYPES.map(t => <SelectItem key={t.value} value={t.value} className="text-[11px]">{t.label}</SelectItem>)}
                                                </SelectContent>
                                            </Select>
                                        </div>

                                        <div className="flex items-center gap-2">
                                            <div className="flex-1 flex items-center bg-background rounded border h-6 px-1.5 border-border/60">
                                                <Hash className="h-2.5 w-2.5 text-muted-foreground mr-1" />
                                                <Input
                                                    type="number"
                                                    value={section.numQuestions}
                                                    onChange={(e) => updateSection(section.id, { numQuestions: parseInt(e.target.value) || 0 })}
                                                    className="h-full border-none shadow-none text-[11px] font-bold p-0 focus-visible:ring-0"
                                                />
                                            </div>
                                            <div className="flex-1 flex items-center bg-background rounded border h-6 px-1.5 border-border/60">
                                                <Award className="h-2.5 w-2.5 text-muted-foreground mr-1" />
                                                <Input
                                                    type="number"
                                                    value={section.marksPerQuestion}
                                                    onChange={(e) => updateSection(section.id, { marksPerQuestion: parseInt(e.target.value) || 0 })}
                                                    className="h-full border-none shadow-none text-[11px] font-bold p-0 focus-visible:ring-0"
                                                />
                                            </div>
                                            <div className="h-6 px-2 flex items-center bg-emerald-500/10 border border-emerald-500/20 rounded-md">
                                                <span className="text-[10px] font-black text-emerald-700">{section.totalMarks}M</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Allocation Meter */}
                        <div className="px-1 space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Weightage Status</span>
                                <span className={cn(
                                    "text-[10px] font-bold px-2 py-0.5 rounded border",
                                    isMatched ? "text-emerald-600 bg-emerald-50 border-emerald-200" :
                                        isExceeded ? "text-destructive bg-destructive/5 border-destructive/20" :
                                            "text-amber-600 bg-amber-50 border-amber-200"
                                )}>
                                    {totalAllocated} / {totalMarks} Marks
                                </span>
                            </div>
                            <div className="h-1 w-full bg-muted rounded-full overflow-hidden flex">
                                <div
                                    className={cn(
                                        "h-full transition-all duration-500",
                                        isExceeded ? "bg-destructive w-full" : isMatched ? "bg-emerald-500 w-full" : "bg-amber-500"
                                    )}
                                    style={{ width: isExceeded ? '100%' : `${(totalAllocated / totalMarks) * 100}%` }}
                                />
                            </div>
                            {error && (
                                <div className="flex items-center gap-1.5 text-[10px] text-destructive font-bold bg-destructive/5 p-2 rounded border border-destructive/10 animate-in shake-in">
                                    <AlertCircle className="h-3 w-3" />
                                    {error}
                                </div>
                            )}
                        </div>

                        <Separator className="opacity-40" />

                        <Button
                            className="w-full h-9 font-black text-[11px] uppercase tracking-widest bg-primary hover:bg-primary/90 shadow-xl shadow-primary/10"
                            onClick={handleApply}
                            disabled={isExceeded}
                        >
                            Apply Pattern <ChevronRight className="h-3.5 w-3.5 ml-1" />
                        </Button>
                    </div>
                ) : (
                    <div className="space-y-4 py-1 animate-in slide-in-from-bottom-2 duration-400">
                        <div className="space-y-3 px-1">
                            {steps.map((step, idx) => {
                                const isActive = step.status === "running";
                                const isDone = step.status === "completed";

                                return (
                                    <div key={idx} className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className={cn(
                                                "h-1.5 w-1.5 rounded-full transition-all duration-300",
                                                isActive ? "bg-emerald-500 animate-pulse scale-150 shadow-[0_0_10px_rgba(16,185,129,0.7)]" : "bg-border",
                                                isDone ? "bg-emerald-500" : ""
                                            )} />
                                            <span className={cn(
                                                "text-[11px] font-bold tracking-tight",
                                                isActive ? "text-foreground" : "text-muted-foreground/60",
                                                isDone ? "text-muted-foreground/40" : ""
                                            )}>
                                                {step.label}
                                            </span>
                                        </div>
                                        {isActive && <Loader2 className="h-3 w-3 animate-spin text-emerald-600" />}
                                        {isDone && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />}
                                    </div>
                                );
                            })}
                        </div>

                        {status === "completed" && (
                            <div className="p-3 bg-emerald-500/5 rounded-lg border border-emerald-200/50 flex flex-col gap-2 animate-in zoom-in-95">
                                <div className="flex items-center gap-2">
                                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                                    <span className="text-[11px] font-black text-emerald-700 uppercase">Success</span>
                                </div>
                                <p className="text-[10px] font-medium text-emerald-700 leading-tight">
                                    Weightage verified across {sections.length} sections. The blueprint is now structurally sound.
                                </p>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
