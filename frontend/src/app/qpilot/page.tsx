"use client";

/**
 * app/qpilot/page.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * QPilot Metadata Configuration Page.
 * Landing page to configure exam details before starting AI generation.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { QPilotSidebar } from "@/components/qpilot/QPilotSidebar";
import { QPilotMetadataForm } from "@/components/qpilot/QPilotMetadataForm";
import { useQPilotConfigStore } from "@/store/qpilotConfigStore";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Rocket, Loader2, ArrowRight, ShieldCheck } from "lucide-react";
import { generatePaper } from "@/lib/projectApi";
import { Separator } from "@/components/ui/separator";

export default function QPilotConfigPage() {
    const router = useRouter();
    const {
        metadata,
        isSubmitting,
        setSubmitting,
        setMetadata,
        reset
    } = useQPilotConfigStore();

    useEffect(() => {
        return () => reset(); // Cleanup on unmount
    }, [reset]);

    const handleAutoFill = () => {
        setMetadata({
            title: "Midterm Mathematics",
            subject: "Mathematics",
            grade: "12",
            totalMarks: 80,
            duration: "3 Hours",
            instructions: "Focus on calculus and integration. Avoid repetition from PYQs.",
        });
        toast.success("Form Auto-Filled!");
    };

    const handleStartGenerate = async () => {
        // 1. Validations
        if (!metadata.title || !metadata.subject || !metadata.grade) {
            toast.error("Missing Metadata", { description: "Please fill in the Exam Title, Subject, and Grade." });
            return;
        }

        // 2. Execution
        setSubmitting(true);
        console.log("QP Metadata:", metadata);
        const id = toast.loading("Initializing QPilot Engines...");

        try {
            /**
             * Phase 1 & 2 Integration:
             * 1. Collect form values
             * 2. Call backend API route /api/qp-metadata
             * 3. Insert into Neon DB
             */
            const response = await fetch('/api/qp-metadata', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    exam_title: metadata.title,
                    subject: metadata.subject,
                    grade: metadata.grade,
                    total_marks: metadata.totalMarks || 80,
                    duration: metadata.duration || "3 Hours",
                    instructions: metadata.instructions || ""
                })
            });

            const insertedData = await response.json();

            if (response.ok) {
                toast.success("Ready for Launch!", { id });
                /**
                 * Phase 3: Redirect to proj-demo-1 with metaId
                 */
                setTimeout(() => {
                    router.push(`/qpilot/proj-demo-1?metaId=${insertedData.id}`);
                }, 1000);
            } else {
                toast.error("Database Error", { id, description: "The server failed to save the metadata." });
                setSubmitting(false);
            }
        } catch (err) {
            const error = err as { message?: string };
            toast.error("Connection Failed", { id, description: error?.message || "Ensure backend is running." });
            setSubmitting(false);
        }
    };

    return (
        <SidebarProvider style={{
            "--sidebar-width": "240px",
            "--sidebar-width-icon": "70px"
        } as React.CSSProperties}>
            <div className="flex h-screen w-full bg-background overflow-hidden">
                {/* 1️⃣ LEFT SIDEBAR */}
                <QPilotSidebar />

                <SidebarInset className="flex-1 overflow-auto bg-slate-50/30 dark:bg-slate-950/20">
                    <main className="max-w-4xl mx-auto px-6 py-10 space-y-10">

                        {/* Header Section */}
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-[0.2em]">
                                        <Rocket className="h-3 w-3" />
                                        QPilot Interface
                                    </div>
                                    <h1 className="text-3xl font-bold tracking-tight text-foreground">Prepare New Exam</h1>
                                </div>

                                <Button
                                    variant="outline"
                                    onClick={handleAutoFill}
                                    disabled={isSubmitting}
                                    className="border-dashed border-primary/40 bg-primary/5 hover:bg-primary/10 text-primary font-bold text-xs"
                                >
                                    AutoFill Demo
                                </Button>
                            </div>

                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 bg-green-500/10 text-green-600 dark:text-green-400 px-3 py-1 rounded-full text-xs font-bold border border-green-500/20">
                                    <ShieldCheck className="h-3.5 w-3.5" />
                                    System Optimized
                                </div>
                            </div>
                            <p className="text-sm text-muted-foreground">Configure the structural integrity and content requirements of your paper.</p>
                        </div>

                        <Separator className="opacity-50" />

                        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            {/* SECTION 1 — Exam Metadata */}
                            <QPilotMetadataForm />

                            {/* SECTION 2 — Start Generate Button */}
                            <div className="flex items-center justify-between bg-card p-6 rounded-2xl border border-border/60 shadow-md">
                                <div className="space-y-1">
                                    <h3 className="text-sm font-bold text-foreground">Ready for AI Assistance?</h3>
                                    <p className="text-xs text-muted-foreground max-w-sm">Generating a question paper involves multi-agent coordination. Ensure all constraints are defined.</p>
                                </div>

                                <Button
                                    size="lg"
                                    onClick={handleStartGenerate}
                                    disabled={isSubmitting}
                                    className="px-8 h-12 gap-3 text-base font-bold shadow-xl shadow-primary/20"
                                >
                                    {isSubmitting ? (
                                        <Loader2 className="h-5 w-5 animate-spin" />
                                    ) : (
                                        <>
                                            Start Generate
                                            <ArrowRight className="h-5 w-5" />
                                        </>
                                    )}
                                </Button>
                            </div>
                        </div>

                        {/* Institutional Footer */}
                        <div className="py-10 text-center border-t border-border/20">
                            <p className="text-[10px] uppercase font-bold tracking-widest text-muted-foreground/40">
                                QPilot Academic Interface v1.0 • Institutional Grade AI
                            </p>
                        </div>
                    </main>
                </SidebarInset>
            </div>
        </SidebarProvider>
    );
}
