"use client";

/**
 * components/qpilot/LivePaperView.tsx
 */

import { useQPilotStore } from "@/store/qpilotStore";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Sparkles, FileText, BadgeCheck, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export function LivePaperView() {
    const { paperContent, status } = useQPilotStore();

    return (
        <div className="flex flex-col h-full bg-slate-50/50 dark:bg-slate-950/20">

            <div className="flex-1 overflow-y-auto">
                <div className="max-w-[800px] mx-auto p-8 lg:p-12 min-h-full bg-card shadow-sm border-x border-border/40">
                    {paperContent.length === 0 ? (
                        <div className="space-y-12 py-10">
                            <div className="text-center space-y-4">
                                <Skeleton className="h-8 w-48 mx-auto" />
                                <Skeleton className="h-4 w-32 mx-auto" />
                            </div>

                            <div className="space-y-8">
                                <div className="space-y-3">
                                    <Skeleton className="h-6 w-32" />
                                    <Separator />
                                    <div className="space-y-4">
                                        <Skeleton className="h-20 w-full" />
                                        <Skeleton className="h-20 w-full" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-12 animate-in fade-in duration-1000">
                            {/* Institutional Header Sim */}
                            <div className="text-center space-y-2 mb-12 border-b-2 border-primary/10 pb-8">
                                <h1 className="text-xl font-bold uppercase tracking-tight">Standard Question Paper</h1>
                                <p className="text-sm text-muted-foreground font-medium">Academic Session 2025-26</p>
                            </div>

                            {paperContent.map((section) => (
                                <section key={section.id} className="space-y-6">
                                    <div className="flex items-center justify-between">
                                        <h3 className="text-base font-bold text-foreground uppercase tracking-wider">{section.title}</h3>
                                        <Badge variant="outline" className="font-mono text-[10px]">
                                            {section.questions.reduce((sum, q) => sum + q.marks, 0)} Marks Total
                                        </Badge>
                                    </div>
                                    <Separator className="bg-primary/10" />

                                    <div className="space-y-10">
                                        {section.questions.map((q) => (
                                            <div key={q.id} className="group relative pl-8">
                                                <span className="absolute left-0 top-0 font-bold text-muted-foreground/50 group-hover:text-primary transition-colors">
                                                    {q.number}.
                                                </span>
                                                <div className="flex justify-between items-start gap-6">
                                                    <p className="text-sm leading-relaxed text-foreground/90 font-medium italic">
                                                        {q.text}
                                                    </p>
                                                    <span className="text-xs font-bold tabular-nums text-muted-foreground bg-muted px-2 py-0.5 rounded flex-shrink-0">
                                                        [{q.marks} m]
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </section>
                            ))}

                            {status === 'running' && (
                                <div className="py-8 border-t border-dashed space-y-4">
                                    <div className="flex items-center gap-2 text-primary">
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        <span className="text-xs font-bold tracking-widest uppercase">Agent Writing...</span>
                                    </div>
                                    <Skeleton className="h-16 w-full opacity-50" />
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
