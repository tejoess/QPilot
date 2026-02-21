"use client";

/**
 * components/builder/SectionList.tsx
 */

import { useState } from "react";
import { Pencil, Trash2, GripVertical, Plus, Layers } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";

import { SectionDialog } from "@/components/builder/SectionDialog";
import {
    addSection,
    updateSection,
    deleteSection,
} from "@/lib/projectApi";
import { useProjectStore } from "@/store/projectStore";
import type { Section, CreateSectionPayload } from "@/types/api";

const TYPE_LABELS: Record<string, string> = {
    mcq: "MCQ",
    short_answer: "Short",
    long_answer: "Long",
    fill_in_the_blank: "Fill Blank",
    true_false: "T/F",
};

const DIFFICULTY_COLORS: Record<string, string> = {
    easy: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
    medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
    hard: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
};

interface SectionListProps {
    projectId: string;
    sections: Section[];
    isLoading: boolean;
}

export function SectionList({ projectId, sections, isLoading }: SectionListProps) {
    const { addSectionLocal, updateSectionLocal, removeSectionLocal } = useProjectStore();

    const [addOpen, setAddOpen] = useState(false);
    const [editTarget, setEditTarget] = useState<Section | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<Section | null>(null);
    const [isMutating, setIsMutating] = useState(false);

    async function handleAdd(payload: CreateSectionPayload) {
        setIsMutating(true);
        const tempId = `temp-${Date.now()}`;
        const optimistic: Section = {
            id: tempId,
            projectId,
            ...payload,
            totalMarks: payload.numQuestions * payload.marksPerQuestion,
            order: sections.length + 1,
        };
        addSectionLocal(optimistic);
        setAddOpen(false);

        try {
            const saved = await addSection(projectId, payload);
            removeSectionLocal(tempId);
            addSectionLocal(saved);
            toast.success("Section added.");
        } catch (err) {
            removeSectionLocal(tempId);
            toast.error("Failed to add section.");
        } finally {
            setIsMutating(false);
        }
    }

    async function handleEdit(payload: CreateSectionPayload) {
        if (!editTarget) return;
        setIsMutating(true);

        const optimistic: Section = {
            ...editTarget,
            ...payload,
            totalMarks: payload.numQuestions * payload.marksPerQuestion
        };
        updateSectionLocal(optimistic);
        setEditTarget(null);

        try {
            const saved = await updateSection(projectId, editTarget.id, payload);
            updateSectionLocal(saved);
            toast.success("Section updated.");
        } catch (err) {
            updateSectionLocal(editTarget);
            toast.error("Failed to update section.");
        } finally {
            setIsMutating(false);
        }
    }

    async function handleDelete() {
        if (!deleteTarget) return;
        setIsMutating(true);
        const snapshot = [...sections];
        removeSectionLocal(deleteTarget.id);
        setDeleteTarget(null);

        try {
            await deleteSection(projectId, deleteTarget.id);
            toast.success("Section deleted.");
        } catch (err) {
            snapshot.forEach((s) => addSectionLocal(s));
            toast.error("Failed to delete section.");
        } finally {
            setIsMutating(false);
        }
    }

    return (
        <Card className="shadow-sm border-border/60">
            <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                    <div className="space-y-1">
                        <CardTitle className="text-base font-semibold flex items-center gap-2">
                            <Layers className="h-4 w-4 text-muted-foreground" />
                            Question Sections
                        </CardTitle>
                        <CardDescription>Organize your paper into sections.</CardDescription>
                    </div>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setAddOpen(true)}
                        disabled={isLoading || isMutating}
                        className="gap-1.5"
                    >
                        <Plus className="h-3.5 w-3.5" />
                        Add Section
                    </Button>
                </div>
            </CardHeader>

            <CardContent>
                <div className="flex flex-col gap-3">
                    {isLoading ? (
                        <div className="space-y-2">
                            {[1, 2, 3].map((i) => (
                                <Skeleton key={i} className="h-14 w-full rounded-xl" />
                            ))}
                        </div>
                    ) : sections.length === 0 ? (
                        <div className="flex flex-col items-center justify-center gap-3 py-10 text-center border-2 border-dashed rounded-xl">
                            <p className="text-sm text-muted-foreground">No sections yet. Click "Add Section" to begin.</p>
                        </div>
                    ) : (
                        <ScrollArea className="max-h-[400px] pr-4">
                            <div className="space-y-2">
                                {sections.map((section, idx) => (
                                    <div
                                        key={section.id}
                                        className="group flex items-center gap-3 rounded-xl border border-border/50 bg-card p-3 transition-all hover:border-primary/30"
                                    >
                                        <GripVertical className="h-4 w-4 text-muted-foreground/30 group-hover:text-muted-foreground/60 cursor-grab" />

                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm font-semibold truncate">{section.name}</span>
                                                <Badge variant="outline" className="text-[10px] h-4 px-1">{TYPE_LABELS[section.type]}</Badge>
                                            </div>
                                            <div className="flex items-center gap-2 mt-1">
                                                <span className="text-xs text-muted-foreground">
                                                    {section.numQuestions} Qs × {section.marksPerQuestion}m
                                                </span>
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${DIFFICULTY_COLORS[section.difficulty]}`}>
                                                    {section.difficulty}
                                                </span>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-3">
                                            <div className="text-right">
                                                <p className="text-sm font-bold text-foreground">{section.totalMarks}m</p>
                                            </div>
                                            <div className="flex items-center gap-1">
                                                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setEditTarget(section)}>
                                                    <Pencil className="h-3.5 w-3.5" />
                                                </Button>
                                                <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => setDeleteTarget(section)}>
                                                    <Trash2 className="h-3.5 w-3.5" />
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                    )}
                </div>
            </CardContent>

            <SectionDialog
                mode="add"
                open={addOpen}
                onOpenChange={setAddOpen}
                onSubmit={handleAdd}
                isSubmitting={isMutating}
                nextOrder={sections.length + 1}
            />

            <SectionDialog
                mode="edit"
                open={!!editTarget}
                onOpenChange={(o) => !o && setEditTarget(null)}
                initial={editTarget ?? undefined}
                onSubmit={handleEdit}
                isSubmitting={isMutating}
            />

            <AlertDialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Section?</AlertDialogTitle>
                        <AlertDialogDescription>Permanently remove "{deleteTarget?.name}".</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction className="bg-destructive" onClick={handleDelete}>Delete</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </Card>
    );
}
