"use client";

/**
 * app/processing/[projectId]/page.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Processing Page — orchestrates the multi-agent question paper generation.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
    Loader2,
    AlertTriangle,
    CheckCircle,
    ArrowRight,
    RefreshCcw,
    FileText,
    Rocket
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";

import { PipelineSteps } from "@/components/processing/PipelineSteps";
import { LogPanel } from "@/components/processing/LogPanel";
import { ProcessingProgress } from "@/components/processing/ProcessingProgress";

import { useProcessing } from "@/hooks/useProcessing";
import { useProcessingStore } from "@/store/processingStore";
import { getProject } from "@/lib/projectApi";
import type { PaperGenerationRequest } from "@/types/api";

export default function ProcessingPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const router = useRouter();

    const { status, error, resultFilePath, reset } = useProcessingStore();
    const [requestData, setRequestData] = useState<PaperGenerationRequest | null>(null);
    const [isInitializing, setIsInitializing] = useState(true);

    // Fetch project to get the metadata needed for POST /generate-paper
    useEffect(() => {
        async function load() {
            try {
                const project = await getProject(projectId as string);
                setRequestData({
                    subject: project.subject,
                    grade: project.grade,
                    board: project.board
                });
            } catch (err) {
                console.error("Project load error:", err);
                toast.error("Could not load project metadata.");
            } finally {
                setIsInitializing(false);
            }
        }
        load();
    }, [projectId]);

    const { runGeneration } = useProcessing(projectId as string, requestData);

    // Auto-start generation once project data is ready
    useEffect(() => {
        if (requestData && status === "idle") {
            runGeneration();
        }
    }, [requestData, status, runGeneration]);

    // Success redirection
    useEffect(() => {
        if (status === "completed" && resultFilePath) {
            const timer = setTimeout(() => {
                router.push(`/output/${projectId}`);
            }, 3000);
            return () => clearTimeout(timer);
        }
    }, [status, resultFilePath, router, projectId]);

    // Clean up on unmount
    useEffect(() => {
        return () => reset();
    }, [reset]);

    if (isInitializing) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <div className="text-center space-y-4">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
                    <p className="text-sm text-muted-foreground">Initializing generation pipeline...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background/50 flex flex-col">
            <main className="flex-1 mx-auto w-full max-w-5xl p-4 lg:p-10 space-y-8">

                {/* ══ Status Hero ═══════════════════════════════════════════════ */}
                <section className="text-center space-y-4 py-6" aria-live="polite">
                    <div className="inline-flex h-20 w-20 items-center justify-center rounded-full bg-primary/5 border-2 border-primary/10">
                        {status === "completed" ? (
                            <CheckCircle className="h-10 w-10 text-green-500" />
                        ) : status === "failed" ? (
                            <AlertTriangle className="h-10 w-10 text-destructive" />
                        ) : (
                            <Rocket className="h-10 w-10 text-primary animate-pulse" />
                        )}
                    </div>

                    <div className="space-y-1.5">
                        <h1 className="text-2xl font-bold tracking-tight text-foreground">
                            {status === "completed" ? "Generation Complete!" :
                                status === "failed" ? "Generation Failed" :
                                    "Generating Question Paper"}
                        </h1>
                        <p className="text-sm text-muted-foreground max-w-md mx-auto">
                            {status === "completed" ? "Successfully constructed your paper. Redirecting to output..." :
                                status === "failed" ? "An error occurred during the multi-agent pipeline." :
                                    "Our specialized agents are collaborating to build your question paper."}
                        </p>
                    </div>

                    <div className="flex justify-center gap-2">
                        <Badge variant="outline" className="px-3 py-1">
                            Project ID: {projectId}
                        </Badge>
                        {status === "generating" && (
                            <Badge className="bg-blue-500 hover:bg-blue-600 px-3 py-1">
                                Active Session
                            </Badge>
                        )}
                    </div>
                </section>

                {/* ══ Error Alert ═══════════════════════════════════════════════ */}
                {error && (
                    <Alert variant="destructive" className="max-w-2xl mx-auto shadow-lg animate-in fade-in slide-in-from-top-4">
                        <AlertTriangle className="h-4 w-4" />
                        <AlertTitle>Error Detail</AlertTitle>
                        <AlertDescription className="flex items-center justify-between gap-4">
                            <span>{error}</span>
                            <Button size="sm" variant="outline" className="bg-background" onClick={() => runGeneration()}>
                                <RefreshCcw className="h-3.5 w-3.5 mr-2" />
                                Retry
                            </Button>
                        </AlertDescription>
                    </Alert>
                )}

                {/* ══ Middle Section: Steps & Progress ═════════════════════════ */}
                <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8">
                    <div className="space-y-6">
                        <div className="flex items-center justify-between">
                            <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground/70">Pipeline Steps</h2>
                        </div>
                        <PipelineSteps />
                    </div>

                    <aside className="space-y-6">
                        <div className="flex items-center justify-between">
                            <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground/70">Status Panel</h2>
                        </div>
                        <ProcessingProgress />
                        <LogPanel />
                    </aside>
                </div>

                {/* ══ Footer Actions ════════════════════════════════════════════ */}
                <Separator className="opacity-50" />

                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-4">
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                            Agent Connection: High
                        </div>
                        <Separator orientation="vertical" className="h-4" />
                        <div className="flex items-center gap-1.5">
                            <FileText className="h-3.5 w-3.5" />
                            Target: PDF Export
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        {status === "completed" && (
                            <Button onClick={() => router.push(`/output/${projectId}`)}>
                                View Result
                                <ArrowRight className="ml-2 h-4 w-4" />
                            </Button>
                        )}
                        <Button variant="ghost" onClick={() => router.push(`/builder/${projectId}`)}>
                            Back to Builder
                        </Button>
                    </div>
                </div>
            </main>
        </div>
    );
}
