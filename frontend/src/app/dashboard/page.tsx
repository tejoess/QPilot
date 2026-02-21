"use client";

/**
 * app/dashboard/page.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Main Dashboard Home for QPilot.
 * Features: Quick Actions, System Status, Recent Papers, and Floating Orchestrator.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useEffect } from "react";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { QPilotSidebar } from "@/components/qpilot/QPilotSidebar";
import { QuickActionCard } from "@/components/dashboard/QuickActionCard";
import { SystemStatusPanel } from "@/components/dashboard/SystemStatusPanel";
import { RecentPapersTable } from "@/components/dashboard/RecentPapersTable";
import { FloatingOrchestrator } from "@/components/dashboard/FloatingOrchestrator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
    PlusCircle,
    Upload,
    BarChart3,
    Clock,
    LayoutDashboard
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useDashboardStore } from "@/store/dashboardStore";
import { getSystemStats, getRecentPapers } from "@/lib/dashboardApi";

export default function DashboardPage() {
    const router = useRouter();
    const {
        systemStats,
        recentPapers,
        isLoading,
        setSystemStats,
        setRecentPapers,
        setLoading
    } = useDashboardStore();

    useEffect(() => {
        async function initDashboard() {
            setLoading(true);
            try {
                const [stats, papers] = await Promise.all([
                    getSystemStats(),
                    getRecentPapers()
                ]);
                setSystemStats(stats);
                setRecentPapers(papers);
            } catch (error) {
                console.error("Failed to load dashboard data", error);
            } finally {
                setLoading(false);
            }
        }
        initDashboard();
    }, [setSystemStats, setRecentPapers, setLoading]);

    const lastProjectId = recentPapers.length > 0 ? recentPapers[0].id : null;

    return (
        <SidebarProvider style={{
            "--sidebar-width": "240px",
            "--sidebar-width-icon": "70px"
        } as React.CSSProperties}>
            <div className="flex h-screen w-full bg-background overflow-hidden">
                <QPilotSidebar />
                <SidebarInset className="flex-1 overflow-auto bg-slate-50/30 dark:bg-slate-950/20">
                    <ScrollArea className="h-full">
                        <main className="max-w-7xl mx-auto px-8 py-10 space-y-12">

                            {/* Header Section */}
                            <div className="flex items-center justify-between">
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2 text-primary">
                                        <LayoutDashboard className="h-5 w-5" />
                                        <h1 className="text-sm font-black uppercase tracking-[0.3em]">Dashboard</h1>
                                    </div>
                                    <h2 className="text-3xl font-black tracking-tight text-foreground">Welcome back, Professor.</h2>
                                    <p className="text-sm text-muted-foreground font-medium">Manage your question paper generation pipeline and track insights.</p>
                                </div>
                            </div>

                            {/* 🔷 SECTION A — QUICK ACTION CARDS */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                                <QuickActionCard
                                    title="Generate New QP"
                                    description="Start creating a structured exam paper using QPilot."
                                    icon={PlusCircle}
                                    buttonText="Start"
                                    variant="primary"
                                    onClick={() => router.push("/qpilot")}
                                />
                                <QuickActionCard
                                    title="Upload PYQs"
                                    description="Add new PYQs to strengthen generation quality."
                                    icon={Upload}
                                    buttonText="Upload"
                                    onClick={() => router.push("/history")}
                                />
                                <QuickActionCard
                                    title="View Analytics"
                                    description="Track performance, generation trends, and usage."
                                    icon={BarChart3}
                                    buttonText="View"
                                    onClick={() => router.push("/analytics")}
                                />
                                <QuickActionCard
                                    title="Recent Paper"
                                    description="Continue working on your latest draft."
                                    icon={Clock}
                                    buttonText="Open"
                                    onClick={() => lastProjectId ? router.push(`/qpilot/${lastProjectId}`) : router.push("/qpilot")}
                                />
                            </div>

                            {/* 🔷 SECTION B — SYSTEM STATUS PANEL */}
                            <div className="space-y-4">
                                <div className="flex items-center gap-2">
                                    <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                    <h3 className="text-[11px] font-black uppercase tracking-widest text-muted-foreground/80">System Live Insights</h3>
                                </div>
                                <SystemStatusPanel stats={systemStats} isLoading={isLoading} />
                            </div>

                            <Separator className="opacity-40" />

                            {/* 🔷 SECTION C — RECENT PAPERS TABLE */}
                            <div className="space-y-6">
                                <div className="flex items-center justify-between">
                                    <div className="space-y-1">
                                        <h3 className="text-xl font-black tracking-tight text-foreground">Recent Projects</h3>
                                        <p className="text-xs text-muted-foreground font-medium">Detailed overview of your latest question paper activity.</p>
                                    </div>
                                </div>
                                <RecentPapersTable papers={recentPapers} isLoading={isLoading} />
                            </div>

                        </main>
                    </ScrollArea>
                </SidebarInset>

                {/* 🤖 FLOATING ORCHESTRATOR */}
                <FloatingOrchestrator />
            </div>
        </SidebarProvider>
    );
}
