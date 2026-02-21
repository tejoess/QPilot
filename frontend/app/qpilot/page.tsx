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
        reset
    } = useQPilotConfigStore();

    useEffect(() => {
        return () => reset(); // Cleanup on unmount
    }, [reset]);

    const handleStartGenerate = async () => {
        // 1. Validations
        if (!metadata.title || !metadata.subject || !metadata.grade) {
            toast.error("Missing Metadata", { description: "Please fill in the Exam Title, Subject, and Grade." });
            return;
        }

        // 2. Execution
        setSubmitting(true);
        const id = toast.loading("Initializing QPilot Engines...");

        try {
            /**
             * Integration point: Trigger generation.
             * Route: POST /generate-paper
             * Payload: { subject, grade, board }
             */
            const response = await generatePaper({
                subject: metadata.subject,
                grade: metadata.grade,
                board: metadata.board,
            });

            if (response.status === "success") {
                toast.success("Ready for Launch!", { id });

                // As per request: redirect to proj-demo-1
                // In a real app, we'd use an ID from the backend if available.
                setTimeout(() => {
                    router.push("/qpilot/proj-demo-1");
                }, 1000);
            } else {
                toast.error("Backend Error", { id, description: "The server failed to initialize the session." });
                setSubmitting(false);
            }
        } catch (err: any) {
            toast.error("Connection Failed", { id, description: err?.message || "Ensure backend is running on port 8000." });
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
                        <div className="space-y-2">
                            <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-[0.2em]">
                                <Rocket className="h-3 w-3" />
                                QPilot Interface
                            </div>
                            <div className="flex items-center justify-between">
                                <h1 className="text-3xl font-bold tracking-tight text-foreground">Prepare New Exam</h1>
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
