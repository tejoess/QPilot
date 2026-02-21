"use client";

/**
 * components/builder/LivePreview.tsx
 *
 * Right-column preview card.
 */

import { FileText, Layers } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import type { Section } from "@/types/api";

const TYPE_ICONS: Record<string, string> = {
    mcq: "①",
    short_answer: "✏️",
    long_answer: "📝",
    fill_in_the_blank: "___",
    true_false: "T/F",
};

interface LivePreviewProps {
    sections: Section[];
    projectName: string;
    subject: string;
    grade: string;
    board: string;
    isLoading: boolean;
}

export function LivePreview({
    sections,
    projectName,
    subject,
    grade,
    board,
    isLoading,
}: LivePreviewProps) {
    const totalMarks = sections.reduce((s, sec) => s + sec.totalMarks, 0);

    return (
        <div
            className="flex flex-col gap-4 h-full"
            aria-label="Live paper structure preview"
        >
            <div className="rounded-xl border border-dashed border-border/70 bg-muted/30 p-4">
                {isLoading ? (
                    <div className="space-y-2">
                        <Skeleton className="h-5 w-3/4 rounded" />
                        <Skeleton className="h-3.5 w-1/2 rounded" />
                        <Skeleton className="h-3 w-1/3 rounded" />
                    </div>
                ) : (
                    <div className="space-y-1 text-center">
                        <div className="flex items-center justify-center gap-2 mb-2">
                            <FileText className="h-4 w-4 text-muted-foreground" />
                            <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                                Question Paper Preview
                            </span>
                        </div>
                        <p className="text-sm font-bold text-foreground leading-snug">
                            {projectName || "Untitled Paper"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                            {subject && `${subject} · `}Grade {grade} · {board}
                        </p>
                        {totalMarks > 0 && (
                            <Badge variant="secondary" className="text-xs mt-1">
                                Total: {totalMarks} marks
                            </Badge>
                        )}
                    </div>
                )}
            </div>

            <div className="flex flex-col gap-2 flex-1 overflow-auto">
                {isLoading ? (
                    <div className="space-y-2" aria-busy="true">
                        {[1, 2, 3].map((i) => (
                            <div
                                key={i}
                                className="rounded-lg border border-border/40 bg-card p-3 space-y-1.5"
                            >
                                <Skeleton className="h-4 w-2/3 rounded" />
                                <Skeleton className="h-3 w-1/3 rounded" />
                            </div>
                        ))}
                    </div>
                ) : sections.length === 0 ? (
                    <div className="flex flex-1 flex-col items-center justify-center gap-2 py-8 text-center">
                        <Layers className="h-8 w-8 text-muted-foreground/40" />
                        <p className="text-xs text-muted-foreground max-w-[160px]">
                            Add sections on the left to see the paper structure here.
                        </p>
                    </div>
                ) : (
                    sections.map((section, idx) => (
                        <div
                            key={section.id}
                            className="group rounded-xl border border-border/50 bg-card p-3
                         transition-all hover:border-primary/30 hover:shadow-sm"
                            aria-label={`Preview: ${section.name}`}
                        >
                            <div className="flex items-start gap-2.5">
                                <span
                                    className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center
                             rounded-full bg-primary/10 text-xs font-bold text-primary"
                                    aria-hidden="true"
                                >
                                    {idx + 1}
                                </span>

                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-semibold text-foreground leading-snug truncate">
                                        {section.name}
                                    </p>

                                    <div className="mt-1.5 space-y-0.5">
                                        {Array.from({ length: Math.min(3, Math.ceil(section.totalMarks / 5)) }).map(
                                            (_, qi) => (
                                                <div
                                                    key={qi}
                                                    className="flex items-center gap-1.5"
                                                    aria-hidden="true"
                                                >
                                                    <span className="text-xs text-muted-foreground/60">
                                                        {TYPE_ICONS[section.type] ?? "?"}
                                                    </span>
                                                    <div className="h-1.5 rounded-full bg-muted flex-1" />
                                                </div>
                                            )
                                        )}
                                    </div>
                                </div>

                                <Badge
                                    variant="outline"
                                    className="flex-shrink-0 text-xs tabular-nums"
                                    aria-label={`${section.totalMarks} marks`}
                                >
                                    {section.totalMarks}m
                                </Badge>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {!isLoading && sections.length > 0 && (
                <p className="text-[11px] text-center text-muted-foreground/60 italic">
                    Visual preview only · Actual questions generated on processing
                </p>
            )}
        </div>
    );
}
