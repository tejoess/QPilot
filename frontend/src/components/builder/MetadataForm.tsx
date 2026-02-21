"use client";

/**
 * components/builder/MetadataForm.tsx
 */

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Loader2, Save, FileText } from "lucide-react";
import type { PaperType } from "@/types/api";

const CLASSES = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"];

interface MetadataFormProps {
    data: {
        name: string;
        subject: string;
        grade: string;
        board: string;
        paperType: PaperType;
        totalMarks: number;
        duration: string;
        instructions: string;
    };
    onChange: (updates: Partial<MetadataFormProps["data"]>) => void;
    onSave: () => void;
    isSaving: boolean;
    isLoading: boolean;
}

export function MetadataForm({ data, onChange, onSave, isSaving, isLoading }: MetadataFormProps) {
    if (isLoading) {
        return (
            <Card className="shadow-sm border-border/60">
                <CardContent className="pt-6 space-y-4">
                    <div className="h-4 w-1/4 bg-muted animate-pulse rounded" />
                    <div className="h-10 w-full bg-muted animate-pulse rounded" />
                    <div className="h-10 w-full bg-muted animate-pulse rounded" />
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="shadow-sm border-border/60">
            <CardHeader className="pb-4">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    Exam Metadata
                </CardTitle>
                <CardDescription>Configure basic paper details and instructions.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-1.5">
                    <Label htmlFor="exam-title">Exam Title</Label>
                    <Input
                        id="exam-title"
                        value={data.name}
                        onChange={(e) => onChange({ name: e.target.value })}
                        placeholder="e.g. Periodic Test 1"
                    />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                        <Label htmlFor="subject">Subject</Label>
                        <Input
                            id="subject"
                            value={data.subject}
                            onChange={(e) => onChange({ subject: e.target.value })}
                            placeholder="e.g. Mathematics"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="class">Class/Grade</Label>
                        <Select value={data.grade} onValueChange={(v) => onChange({ grade: v })}>
                            <SelectTrigger id="class">
                                <SelectValue placeholder="Select" />
                            </SelectTrigger>
                            <SelectContent>
                                {CLASSES.map((c) => (
                                    <SelectItem key={c} value={c}>Class {c}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                        <Label htmlFor="total-marks">Total Marks</Label>
                        <Input
                            id="total-marks"
                            type="number"
                            value={data.totalMarks}
                            onChange={(e) => onChange({ totalMarks: parseInt(e.target.value) || 0 })}
                        />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="duration">Duration</Label>
                        <Input
                            id="duration"
                            value={data.duration}
                            onChange={(e) => onChange({ duration: e.target.value })}
                            placeholder="e.g. 3 Hours"
                        />
                    </div>
                </div>

                <div className="space-y-1.5">
                    <Label htmlFor="instructions">Instructions</Label>
                    <Textarea
                        id="instructions"
                        value={data.instructions}
                        onChange={(e) => onChange({ instructions: e.target.value })}
                        placeholder="Enter instructions for students..."
                        className="min-h-[100px]"
                    />
                </div>

                <Button onClick={onSave} disabled={isSaving} className="w-full gap-2">
                    {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Save Changes
                </Button>
            </CardContent>
        </Card>
    );
}
