"use client";

/**
 * components/builder/SectionDialog.tsx
 */

import { useEffect, useState } from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Loader2 } from "lucide-react";
import type { CreateSectionPayload, SectionType, DifficultyLevel } from "@/types/api";

const SECTION_TYPES: { value: SectionType; label: string }[] = [
    { value: "mcq", label: "Multiple Choice (MCQ)" },
    { value: "short_answer", label: "Short Answer" },
    { value: "long_answer", label: "Long Answer" },
    { value: "fill_in_the_blank", label: "Fill in the Blank" },
    { value: "true_false", label: "True / False" },
];

const DIFFICULTY_LEVELS: { value: DifficultyLevel; label: string }[] = [
    { value: "easy", label: "Easy" },
    { value: "medium", label: "Medium" },
    { value: "hard", label: "Hard" },
];

interface SectionDialogProps {
    mode: "add" | "edit";
    open: boolean;
    onOpenChange: (open: boolean) => void;
    initial?: Partial<CreateSectionPayload>;
    onSubmit: (payload: CreateSectionPayload) => void;
    isSubmitting?: boolean;
    nextOrder?: number;
}


export function SectionDialog({
    mode,
    open,
    onOpenChange,
    initial,
    onSubmit,
    isSubmitting = false,
    nextOrder = 1,
}: SectionDialogProps) {
    const [form, setForm] = useState<CreateSectionPayload>({
        name: initial?.name ?? "",
        type: initial?.type ?? "mcq",
        numQuestions: initial?.numQuestions ?? 10,
        marksPerQuestion: initial?.marksPerQuestion ?? 1,
        difficulty: initial?.difficulty ?? "medium",
        order: initial?.order ?? nextOrder,
    });
    const [errors, setErrors] = useState<Record<string, string>>({});

    // Reset form when dialog opens or initial values change
    useEffect(() => {
        if (open) {
            setForm({
                name: initial?.name ?? "",
                type: initial?.type ?? "mcq",
                numQuestions: initial?.numQuestions ?? 10,
                marksPerQuestion: initial?.marksPerQuestion ?? 1,
                difficulty: initial?.difficulty ?? "medium",
                order: initial?.order ?? nextOrder,
            });
            setErrors({});
        }
    }, [open, initial, nextOrder]);

    function validate(): boolean {
        const errs: Record<string, string> = {};
        if (!form.name.trim()) errs.name = "Section name is required.";
        if (form.numQuestions < 1) errs.numQuestions = "Must have at least 1 question.";
        if (form.marksPerQuestion < 1) errs.marksPerQuestion = "Marks must be at least 1.";
        setErrors(errs);
        return Object.keys(errs).length === 0;
    }

    function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!validate()) return;
        onSubmit({ ...form });
    }

    function setField<K extends keyof CreateSectionPayload>(
        key: K,
        value: CreateSectionPayload[K]
    ) {
        setForm((prev) => ({ ...prev, [key]: value }));
        setErrors((prev) => ({ ...prev, [key]: "" }));
    }

    const title = mode === "add" ? "Add Section" : "Edit Section";
    const submitLabel = mode === "add" ? "Add Section" : "Save Changes";
    const computedTotal = form.numQuestions * form.marksPerQuestion;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                    <DialogDescription>
                        Configure the questions and marks for this section.
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-4 py-2">
                    <div className="space-y-1.5">
                        <Label htmlFor="section-name">Section Title</Label>
                        <Input
                            id="section-name"
                            placeholder="e.g. Section A"
                            value={form.name}
                            onChange={(e) => setField("name", e.target.value)}
                            className={errors.name ? "border-destructive" : ""}
                        />
                        {errors.name && <p className="text-xs text-destructive">{errors.name}</p>}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <Label htmlFor="section-type">Question Type</Label>
                            <Select
                                value={form.type}
                                onValueChange={(v) => setField("type", v as SectionType)}
                            >
                                <SelectTrigger id="section-type">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {SECTION_TYPES.map((t) => (
                                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="section-difficulty">Difficulty</Label>
                            <Select
                                value={form.difficulty}
                                onValueChange={(v) => setField("difficulty", v as DifficultyLevel)}
                            >
                                <SelectTrigger id="section-difficulty">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {DIFFICULTY_LEVELS.map((t) => (
                                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <Label htmlFor="num-q">No. of Questions</Label>
                            <Input
                                id="num-q"
                                type="number"
                                min={1}
                                value={form.numQuestions}
                                onChange={(e) => setField("numQuestions", parseInt(e.target.value) || 0)}
                            />
                            {errors.numQuestions && <p className="text-xs text-destructive">{errors.numQuestions}</p>}
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="marks-per">Marks per Q</Label>
                            <Input
                                id="marks-per"
                                type="number"
                                min={1}
                                value={form.marksPerQuestion}
                                onChange={(e) => setField("marksPerQuestion", parseInt(e.target.value) || 0)}
                            />
                            {errors.marksPerQuestion && <p className="text-xs text-destructive">{errors.marksPerQuestion}</p>}
                        </div>
                    </div>

                    <div className="p-3 bg-muted rounded-lg flex justify-between items-center">
                        <span className="text-sm font-medium text-muted-foreground">Total Section Marks</span>
                        <span className="text-lg font-bold text-foreground">{computedTotal}</span>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" type="button" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isSubmitting}>
                            {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : submitLabel}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
