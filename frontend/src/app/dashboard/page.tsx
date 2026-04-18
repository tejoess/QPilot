"use client";

/**
 * app/dashboard/page.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Main Dashboard Home for QPilot.
 * Features: Quick Actions, System Status, Recent Papers, and Floating Orchestrator.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useEffect } from "react";
import { motion } from "framer-motion";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { QPilotSidebar } from "@/components/qpilot/QPilotSidebar";
import { QuickActionCard } from "@/components/dashboard/QuickActionCard";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
    PlusCircle,
    LayoutDashboard,
    FileText,
    Download,
    Eye,
    Trash
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { useDashboardStore } from "@/store/dashboardStore";
import { getUserProjects, deleteProjectFromDb } from "@/actions/dashboardActions";
import { toast } from "sonner";

export default function DashboardPage() {
    const router = useRouter();
    const {
        recentPapers,
        isLoading,
        setRecentPapers,
        setLoading
    } = useDashboardStore();

    useEffect(() => {
        async function initDashboard() {
            setLoading(true);
            try {
                const rawPapers = await getUserProjects();
                
                // Map DB schema to UI expected shape
                const papers = rawPapers.map(p => ({
                    id: p.id,
                    name: p.name,
                    subject: p.subject || "Subject",
                    grade: p.grade || "N/A",
                    board: "CBSE",
                    paperType: "cbse" as any,
                    totalMarks: p.totalMarks || 80,
                    duration: p.duration || "3 Hours",
                    instructions: "N/A",
                    status: (p.status || "draft") as any,
                    settings: (p.settings as any) || { includeAnswerKey: true, shuffleQuestions: false, negativeMarking: false, difficultyDistribution: [30, 40, 30] },
                    createdAt: p.createdAt.toISOString(),
                    updatedAt: p.updatedAt.toISOString(),
                    pdfUrl: p.pdfUrl || undefined,
                }));
                
                setRecentPapers(papers);
            } catch (error) {
                console.error("Failed to load dashboard data", error);
            } finally {
                setLoading(false);
            }
        }
        initDashboard();
    }, [setRecentPapers, setLoading]);

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

                            {/* 🔷 GENERATED PAPERS GRID */}
                            <div className="space-y-4 pt-4">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-black uppercase tracking-widest text-muted-foreground">Generated Papers</h3>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                                    {/* Create New Card */}
                                    <QuickActionCard
                                        title="Generate New QP"
                                        description="Start creating a structured exam paper using QPilot."
                                        icon={PlusCircle}
                                        buttonText="Start"
                                        variant="primary"
                                        onClick={() => router.push("/qpilot")}
                                    />
                                    {/* Map existing papers */}
                                    {recentPapers.map((paper, index) => (
                                        <Card key={paper.id || index} className="group relative overflow-hidden transition-all duration-300 hover:shadow-xl hover:-translate-y-1 border-border/50 bg-card">
                                            <CardContent className="p-6 space-y-4">
                                                <div className="flex justify-between items-start">
                                                    <div className="p-3 rounded-xl w-fit bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                                                        <FileText className="h-6 w-6" />
                                                    </div>
                                                    <div className="flex items-center gap-1 text-[10px] text-emerald-600 font-bold bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">Azure</div>
                                                </div>
                                                <div className="space-y-1.5 h-16">
                                                    <h3 className="font-bold text-[14px] leading-snug tracking-tight text-foreground line-clamp-2 group-hover:text-primary transition-colors">{paper.name}</h3>
                                                    <div className="flex flex-wrap gap-1.5 mt-1">
                                                        <span className="text-[10px] font-bold text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded uppercase tracking-wider">{paper.subject}</span>
                                                        <span className="text-[10px] font-bold text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded uppercase tracking-wider">{paper.grade}</span>
                                                        <span className="text-[10px] font-black text-primary bg-primary/5 px-1.5 py-0.5 rounded border border-primary/20">{paper.totalMarks}M</span>
                                                    </div>
                                                </div>
                                                <div className="flex gap-2 w-full">
                                                    <Button variant="outline" size="sm" className="flex-1 text-xs shadow-none px-2" onClick={() => router.push(`/qpilot/${paper.id}/resultqp`)}><Eye className="h-3 w-3 mr-1 shrink-0"/> View</Button>
                                                    <Button variant="outline" size="sm" className="flex-1 text-xs shadow-none px-2" onClick={() => window.open(paper.pdfUrl, '_blank')} disabled={!paper.pdfUrl}><Download className="h-3 w-3 mr-1 shrink-0"/> Download</Button>
                                                </div>
                                                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                                                    <Button 
                                                        variant="ghost" 
                                                        size="sm" 
                                                        className="w-full text-xs text-destructive hover:bg-destructive/10 mt-2"
                                                        onClick={async () => {
                                                            const ok = await deleteProjectFromDb(paper.id);
                                                            if (ok) {
                                                                setRecentPapers(recentPapers.filter(p => p.id !== paper.id));
                                                                toast.success("Deleted project");
                                                            } else {
                                                                toast.error("Failed to delete project");
                                                            }
                                                        }}
                                                    >
                                                        <Trash className="h-3 w-3 mr-1"/> Delete Project
                                                    </Button>
                                                </motion.div>
                                            </CardContent>
                                        </Card>
                                    ))}
                                </div>
                            </div>

                        </main>
                    </ScrollArea>
                </SidebarInset>
            </div>
        </SidebarProvider>
    );
}
