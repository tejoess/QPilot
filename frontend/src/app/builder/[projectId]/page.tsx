"use client";

/**
 * app/builder/[projectId]/page.tsx
 */

import { useEffect, useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import {
    ArrowRight,
    ChevronRight,
    Loader2,
    Sparkles,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

import { SectionList } from "@/components/builder/SectionList";
import { MetadataForm } from "@/components/builder/MetadataForm";
import { GenerationSettings } from "@/components/builder/GenerationSettings";
import { SummaryCard } from "@/components/builder/SummaryCard";

import {
    getProject,
    getSections,
    updateProject,
    generatePaper,
} from "@/lib/projectApi";
import {
    useProjectStore,
} from "@/store/projectStore";

import type { UpdateProjectPayload, Project } from "@/types/api";

const STATUS_VARIANT: Record<string, string> = {
    draft: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
    processing: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
    done: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
    error: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
};

export default function BuilderPage() {
    const params = useParams<{ projectId: string }>();
    const router = useRouter();
    const projectId = params?.projectId ?? "";

    // ── Zustand ───────────────────────────────────────────────────────────────
    const {
        project,
        sections,
        isLoadingProject,
        isLoadingSections,
        isSavingProject,
        setProject,
        setSections,
        setLoadingProject,
        setLoadingSections,
        setSavingProject,
        resetBuilder,
        updateProjectLocal,
        isValid
    } = useProjectStore();

    const totalMarks = sections.reduce((s, sec) => s + sec.totalMarks, 0); // Moved here to be in scope

    const [isGenerating, setIsGenerating] = useState(false);

    useEffect(() => {
        return () => resetBuilder();
    }, [resetBuilder]);

    const fetchProject = useCallback(async () => {
        if (!projectId) return;
        setLoadingProject(true);
        try {
            const data = await getProject(projectId);
            setProject(data);
        } catch (err) {
            console.error("Project fetch error:", err);
            toast.error("Could not load project.");
        } finally {
            setLoadingProject(false);
        }
    }, [projectId, setProject, setLoadingProject]);

    const fetchSections = useCallback(async () => {
        if (!projectId) return;
        setLoadingSections(true);
        try {
            const data = await getSections(projectId);
            setSections(data);
        } catch (err) {
            console.error("Sections fetch error:", err);
            toast.error("Could not load sections.");
        } finally {
            setLoadingSections(false);
        }
    }, [projectId, setSections, setLoadingSections]);

    useEffect(() => {
        fetchProject();
        fetchSections();
    }, [fetchProject, fetchSections]);

    const handleMetadataChange = (updates: Partial<Project>) => {
        updateProjectLocal(updates);
    };

    const handleSettingsChange = (updates: Partial<Project["settings"]>) => {
        if (!project) return;
        updateProjectLocal({
            settings: { ...project.settings, ...updates }
        });
    };

    const handleSaveAll = async () => {
        if (!project) return;
        setSavingProject(true);
        try {
            const saved = await updateProject(project.id, project as UpdateProjectPayload);
            setProject(saved);
            toast.success("Project updated.");
        } catch (err) {
            console.error("Save error:", err);
            toast.error("Failed to save.");
        } finally {
            setSavingProject(false);
        }
    };

    const handleGenerate = async () => {
        if (!project) return;
        if (!isValid()) {
            toast.error("Validation failed.", {
                description: "Total section marks must equal total paper marks."
            });
            return;
        }

        setIsGenerating(true);
        try {
            const result = await generatePaper({
                subject: project.subject,
                grade: project.grade,
                board: project.board,
            });

            if (result.status === "success") {
                toast.success("Generation started!");
                router.push(`/processing/${project.id}`);
            } else {
                toast.error("Failed to start generation.");
            }
        } catch (err) {
            console.error("Generation error:", err);
            toast.error("Backend error. Is the server running?");
        } finally {
            setIsGenerating(false);
        }
    };

    const pageIsValid = isValid();

    return (
        <div className="min-h-screen bg-background/50 flex flex-col">
            {/* ══ Topbar ═══════════════════════════════════════════════════════════ */}
            <header className="sticky top-0 z-30 border-b bg-background/80 backdrop-blur-md">
                <div className="mx-auto max-w-[1400px] px-4 h-14 flex items-center justify-between">
                    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm text-muted-foreground mr-4 min-w-0">
                        <button onClick={() => router.push("/")} className="hover:text-foreground transition-colors truncate">Projects</button>
                        <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />
                        {isLoadingProject ? <Skeleton className="h-4 w-24" /> : <span className="text-foreground font-medium truncate">{project?.name}</span>}
                        <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />
                        <span className="text-primary font-bold">Builder</span>

                        {!isLoadingProject && project && (
                            <>
                                <Badge variant="secondary" className={`ml-3 hidden sm:inline-flex text-[10px] capitalize ${STATUS_VARIANT[project.status]}`}>
                                    {project.status}
                                </Badge>
                                <Badge
                                    variant="outline"
                                    className="ml-2 flex-shrink-0 text-xs tabular-nums"
                                    aria-label={`${totalMarks} marks`}
                                >
                                    {totalMarks}m
                                </Badge>
                            </>
                        )}
                    </nav>

                    <div className="flex items-center gap-3">
                        <Button
                            size="sm"
                            onClick={handleGenerate}
                            disabled={isLoadingProject || isLoadingSections || isGenerating || !pageIsValid}
                            className="gap-2 shadow-sm font-semibold"
                        >
                            {isGenerating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                            Generate Paper
                        </Button>
                    </div>
                </div>
            </header>

            {/* ══ Main View ═════════════════════════════════════════════════════════ */}
            <main className="flex-1 mx-auto w-full max-w-[1400px] p-4 lg:p-6">
                <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 items-start">

                    {/* ── LEFT: FORM & LIST ────────────────────────────────────────── */}
                    <div className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <MetadataForm
                                data={project ? {
                                    name: project.name,
                                    subject: project.subject,
                                    grade: project.grade,
                                    board: project.board,
                                    paperType: project.paperType,
                                    totalMarks: project.totalMarks,
                                    duration: project.duration,
                                    instructions: project.instructions
                                } : { name: "", subject: "", grade: "", board: "", paperType: "cbse", totalMarks: 100, duration: "", instructions: "" }}
                                onChange={handleMetadataChange}
                                onSave={handleSaveAll}
                                isSaving={isSavingProject}
                                isLoading={isLoadingProject}
                            />
                            <GenerationSettings
                                settings={project?.settings || { includeAnswerKey: true, shuffleQuestions: false, negativeMarking: false, difficultyDistribution: [30, 40, 30] }}
                                onChange={handleSettingsChange}
                                isLoading={isLoadingProject}
                            />
                        </div>

                        <SectionList
                            projectId={projectId}
                            sections={sections}
                            isLoading={isLoadingSections}
                        />

                        <div className="flex border-t pt-6 justify-between items-center bg-card p-6 rounded-2xl border border-border/60 shadow-sm">
                            <div className="space-y-1">
                                <p className="text-sm font-medium text-muted-foreground">Ready to generate?</p>
                                <p className="text-xs text-muted-foreground">Ensure all sections are correctly configured and marks match.</p>
                            </div>
                            <Button
                                size="lg"
                                onClick={handleGenerate}
                                disabled={!pageIsValid || isGenerating}
                                className="gap-2 px-8 h-12 text-base font-bold"
                            >
                                {isGenerating ? <Loader2 className="h-5 w-5 animate-spin" /> : <ArrowRight className="h-5 w-5" />}
                                Generate Question Paper
                            </Button>
                        </div>
                    </div>

                    {/* ── RIGHT: SUMMARY ────────────────────────────────────────────── */}
                    <aside className="sticky top-20">
                        <SummaryCard
                            project={project}
                            sections={sections}
                            isLoading={isLoadingProject || isLoadingSections}
                        />
                    </aside>
                </div>
            </main>
        </div>
    );
}
