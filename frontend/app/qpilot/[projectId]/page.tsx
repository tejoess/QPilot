"use client";

/**
 * app/qpilot/[projectId]/page.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * QPilot Agent Execution Interface.
 * AI control center focused on monitoring agent workflows and live paper rendering.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { QPilotSidebar } from "@/components/qpilot/QPilotSidebar";
import { AgentPanel } from "@/components/qpilot/AgentPanel";
import { LivePaperView } from "@/components/qpilot/LivePaperView";
import { useQPilotStore } from "@/store/qpilotStore";
import { useQPilotInterface } from "@/hooks/useQPilotInterface";
import { getProject } from "@/lib/projectApi";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import type { PaperGenerationRequest } from "@/types/api";

export default function QPilotExecutionPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const router = useRouter();

    const { status, reset } = useQPilotStore();
    const [requestData, setRequestData] = useState<PaperGenerationRequest | null>(null);
    const [isInitializing, setIsInitializing] = useState(true);

    // 1. Initial Data Fetch
    useEffect(() => {
        async function init() {
            try {
                const project = await getProject(projectId as string);
                setRequestData({
                    subject: project.subject,
                    grade: project.grade,
                    board: project.board
                });
            } catch (err) {
                toast.error("Failed to initialize project session.");
            } finally {
                setIsInitializing(false);
            }
        }
        init();
        return () => reset(); // Cleanup on unmount
    }, [projectId, reset]);

    // 2. Integration Hook
    const { runGeneration } = useQPilotInterface(projectId as string, requestData);

    // 3. Auto-start on load
    useEffect(() => {
        if (requestData && status === "idle") {
            runGeneration();
        }
    }, [requestData, status, runGeneration]);

    // Handle completion delay & redirect
    useEffect(() => {
        if (status === "completed") {
            toast.success("Generation Complete!", {
                description: "Reviewing final document... Redirecting in 3s.",
            });
            const timer = setTimeout(() => {
                router.push(`/output/${projectId}`);
            }, 3500);
            return () => clearTimeout(timer);
        }
    }, [status, projectId, router]);

    if (isInitializing) {
        return (
            <div className="h-screen w-full flex flex-col items-center justify-center bg-background">
                <Loader2 className="h-6 w-6 animate-spin text-primary mb-2" />
                <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Booting Agents...</span>
            </div>
        );
    }

    return (
        <SidebarProvider>
            <div className="flex h-screen w-full overflow-hidden bg-background">
                {/* 1. SIDEBAR */}
                <QPilotSidebar />

                <SidebarInset className="flex-1 overflow-hidden">
                    <div className="flex h-full overflow-hidden">

                        {/* 2. LEFT PANEL (Agents Area) - ~400px fixed width */}
                        <div className="w-[400px] border-r border-border/50 bg-card/10 overflow-hidden flex flex-col">
                            <div className="px-6 py-4 border-b border-border/50 bg-background/50">
                                <h2 className="text-sm font-bold uppercase tracking-[0.2em] text-primary">Multi-Agent Orchestration</h2>
                                <p className="text-[10px] text-muted-foreground uppercase font-medium">Real-time pipeline monitoring</p>
                            </div>
                            <div className="flex-1 overflow-hidden">
                                <AgentPanel />
                            </div>
                        </div>

                        {/* 3. RIGHT PANEL (Live Rendering View) - Fills remaining space */}
                        <main className="flex-1 overflow-hidden bg-muted/20">
                            <LivePaperView />
                        </main>
                    </div>
                </SidebarInset>
            </div>
        </SidebarProvider>
    );
}
