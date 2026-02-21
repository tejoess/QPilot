"use client";

/**
 * components/qpilot/QPilotSectionConfig.tsx
 */

import { useState } from "react";
import { useQPilotConfigStore, type QPilotSection, type QuestionType, type Difficulty } from "@/store/qpilotConfigStore";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
    DialogDescription
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from "@/components/ui/select";
import { Layers, Plus, Pencil, Trash2, AlertCircle } from "lucide-react";

const QUESTION_TYPES: { value: QuestionType; label: string }[] = [
    { value: "mcq", label: "MCQ" },
    { value: "short_answer", label: "Short Answer" },
    { value: "long_answer", label: "Long Answer" },
    { value: "fill_in_the_blank", label: "Fill Blank" },
    { value: "true_false", label: "True / False" },
];

const DIFFICULTIES: Difficulty[] = ["easy", "medium", "hard"];

export function QPilotSectionConfig() {
    const { sections, metadata, addSection, updateSection, removeSection, getTotalSectionMarks } = useQPilotConfigStore();

    const [isOpen, setIsOpen] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [form, setForm] = useState<Omit<QPilotSection, "id">>({
        title: "",
        type: "mcq",
        numQuestions: 5,
        marksPerQuestion: 1,
        difficulty: "medium",
    });

    const openAdd = () => {
        setEditingId(null);
        setForm({ title: "", type: "mcq", numQuestions: 5, marksPerQuestion: 1, difficulty: "medium" });
        setIsOpen(true);
    };

    const openEdit = (section: QPilotSection) => {
        setEditingId(section.id);
        setForm({ ...section });
        setIsOpen(true);
    };

    const handleSave = () => {
        if (!form.title) return;
        if (editingId) {
            updateSection(editingId, form);
        } else {
            addSection(form);
        }
        setIsOpen(false);
    };

    const currentTotal = getTotalSectionMarks();
    const isMarksMatching = currentTotal === metadata.totalMarks;

    return (
        <Card className="border-border/60 shadow-sm overflow-hidden">
            <CardHeader className="bg-muted/30 border-b border-border/50 py-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-primary/10 text-primary">
                            <Layers className="h-5 w-5" />
                        </div>
                        <div>
                            <CardTitle className="text-sm font-bold uppercase tracking-wider">Section Configuration</CardTitle>
                            <CardDescription className="text-xs">Define question types and weightage per section.</CardDescription>
                        </div>
                    </div>
                    <Button size="sm" onClick={openAdd} className="gap-2 h-8">
                        <Plus className="h-4 w-4" />
                        Add Section
                    </Button>
                </div>
            </CardHeader>

            <CardContent className="p-0">
                <div className="flex flex-col">
                    {sections.length === 0 ? (
                        <div className="p-12 text-center flex flex-col items-center gap-3">
                            <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center">
                                <Plus className="h-6 w-6 text-muted-foreground" />
                            </div>
                            <p className="text-sm text-muted-foreground">No sections added. Click the button above to start.</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-border/40">
                            {sections.map((section) => (
                                <div key={section.id} className="p-4 flex items-center justify-between group hover:bg-muted/30 transition-colors">
                                    <div className="flex items-center gap-4">
                                        <div className="h-10 w-10 rounded-lg border border-border/50 bg-background flex flex-col items-center justify-center">
                                            <span className="text-[10px] font-bold text-muted-foreground uppercase">{section.type.charAt(0)}</span>
                                            <span className="text-xs font-bold leading-none">{section.numQuestions}</span>
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-foreground">{section.title}</h4>
                                            <div className="flex items-center gap-2 mt-1">
                                                <Badge variant="outline" className="text-[9px] uppercase tracking-tighter h-4">
                                                    {section.type.replace('_', ' ')}
                                                </Badge>
                                                <Badge className={`text-[9px] uppercase tracking-tighter h-4 font-bold ${section.difficulty === 'easy' ? 'bg-green-500' :
                                                    section.difficulty === 'hard' ? 'bg-destructive' : 'bg-amber-500'
                                                    }`}>
                                                    {section.difficulty}
                                                </Badge>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-6">
                                        <div className="text-right">
                                            <p className="text-sm font-bold text-foreground">{section.numQuestions * section.marksPerQuestion}m</p>
                                            <p className="text-[10px] text-muted-foreground">{section.marksPerQuestion}m per Q</p>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <Button variant="ghost" size="icon" onClick={() => openEdit(section)} className="h-8 w-8 hover:bg-primary/10 hover:text-primary">
                                                <Pencil className="h-3.5 w-3.5" />
                                            </Button>
                                            <Button variant="ghost" size="icon" onClick={() => removeSection(section.id)} className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive">
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </CardContent>

            <CardFooter className="bg-muted/20 border-t border-border/50 p-4 flex items-center justify-between">
                <div className="flex gap-4">
                    <div className="space-y-0.5">
                        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Total Allocated</p>
                        <div className="flex items-center gap-2">
                            <span className={isMarksMatching ? "text-lg font-bold text-green-600" : "text-lg font-bold text-amber-500"}>
                                {currentTotal}
                            </span>
                            <span className="text-xs text-muted-foreground">/ {metadata.totalMarks} marks</span>
                        </div>
                    </div>
                </div>

                {!isMarksMatching && sections.length > 0 && (
                    <div className="flex items-center gap-2 text-[11px] font-medium text-amber-600 animate-pulse">
                        <AlertCircle className="h-3.5 w-3.5" />
                        Marks Mismatch: Difference of {Math.abs(metadata.totalMarks - currentTotal)}
                    </div>
                )}
            </CardFooter>

            {/* Add / Edit Dialog */}
            <Dialog open={isOpen} onOpenChange={setIsOpen}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle>{editingId ? "Edit Section" : "Add New Section"}</DialogTitle>
                        <DialogDescription>
                            Define the questions and marks for this section.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="grid gap-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="sec-title">Section Title</Label>
                            <Input id="sec-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g. Physics - Section A" />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="sec-type">Question Type</Label>
                                <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v as QuestionType })}>
                                    <SelectTrigger id="sec-type">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {QUESTION_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="sec-diff">Difficulty</Label>
                                <Select value={form.difficulty} onValueChange={(v) => setForm({ ...form, difficulty: v as Difficulty })}>
                                    <SelectTrigger id="sec-diff">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {DIFFICULTIES.map(d => <SelectItem key={d} value={d} className="capitalize">{d}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="sec-num">Questions</Label>
                                <Input id="sec-num" type="number" value={form.numQuestions} onChange={(e) => setForm({ ...form, numQuestions: parseInt(e.target.value) || 0 })} />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="sec-marks">Marks per Q</Label>
                                <Input id="sec-marks" type="number" value={form.marksPerQuestion} onChange={(e) => setForm({ ...form, marksPerQuestion: parseInt(e.target.value) || 0 })} />
                            </div>
                        </div>

                        <div className="p-3 bg-muted rounded-lg flex justify-between items-center text-xs">
                            <span className="font-bold text-muted-foreground uppercase tracking-widest">Section Total</span>
                            <span className="text-lg font-bold text-foreground">{form.numQuestions * form.marksPerQuestion} Marks</span>
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsOpen(false)}>Cancel</Button>
                        <Button onClick={handleSave} disabled={!form.title}>Save Section</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}
