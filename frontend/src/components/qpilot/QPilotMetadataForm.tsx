"use client";

/**
 * components/qpilot/QPilotMetadataForm.tsx
 */

import { useQPilotConfigStore } from "@/store/qpilotConfigStore";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from "@/components/ui/select";
import { FileText, GraduationCap, BookOpen, Clock } from "lucide-react";

const GRADES = ["6", "7", "8", "9", "10", "11", "12"];
const BOARDS = ["CBSE", "ICSE", "IGCSE", "State Board"];

export function QPilotMetadataForm() {
    const { metadata, setMetadata } = useQPilotConfigStore();

    return (
        <Card className="border-border/60 shadow-sm overflow-hidden">
            <CardHeader className="bg-muted/30 border-b border-border/50 py-4">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10 text-primary">
                        <GraduationCap className="h-5 w-5" />
                    </div>
                    <div>
                        <CardTitle className="text-sm font-bold uppercase tracking-wider">Exam Metadata</CardTitle>
                        <CardDescription className="text-xs">Configure the basic structure and institutional details.</CardDescription>
                    </div>
                </div>
            </CardHeader>

            <CardContent className="p-6 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Title */}
                    <div className="space-y-2">
                        <Label htmlFor="title" className="text-xs font-bold text-muted-foreground uppercase flex items-center gap-2">
                            <FileText className="h-3 w-3" />
                            Exam Title
                        </Label>
                        <Input
                            id="title"
                            placeholder="e.g. Periodic Test - II"
                            value={metadata.title}
                            onChange={(e) => setMetadata({ title: e.target.value })}
                            className="bg-card"
                        />
                    </div>

                    {/* Subject */}
                    <div className="space-y-2">
                        <Label htmlFor="subject" className="text-xs font-bold text-muted-foreground uppercase flex items-center gap-2">
                            <BookOpen className="h-3 w-3" />
                            Subject
                        </Label>
                        <Input
                            id="subject"
                            placeholder="e.g. Physics"
                            value={metadata.subject}
                            onChange={(e) => setMetadata({ subject: e.target.value })}
                            className="bg-card"
                        />
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Grade */}
                    <div className="space-y-2">
                        <Label htmlFor="grade" className="text-xs font-bold text-muted-foreground uppercase">Grade / Class</Label>
                        <Select value={metadata.grade} onValueChange={(v) => setMetadata({ grade: v })}>
                            <SelectTrigger id="grade" className="bg-card">
                                <SelectValue placeholder="Select Grade" />
                            </SelectTrigger>
                            <SelectContent>
                                {GRADES.map((g) => (
                                    <SelectItem key={g} value={g}>Grade {g}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Board */}
                    <div className="space-y-2">
                        <Label htmlFor="board" className="text-xs font-bold text-muted-foreground uppercase">Education Board</Label>
                        <Select value={metadata.board} onValueChange={(v) => setMetadata({ board: v })}>
                            <SelectTrigger id="board" className="bg-card">
                                <SelectValue placeholder="Select Board" />
                            </SelectTrigger>
                            <SelectContent>
                                {BOARDS.map((b) => (
                                    <SelectItem key={b} value={b}>{b}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Marks */}
                    <div className="space-y-2">
                        <Label htmlFor="totalMarks" className="text-xs font-bold text-muted-foreground uppercase">Total Marks</Label>
                        <Input
                            id="totalMarks"
                            type="number"
                            value={metadata.totalMarks}
                            onChange={(e) => setMetadata({ totalMarks: parseInt(e.target.value) || 0 })}
                            className="bg-card"
                        />
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[160px_1fr] gap-6">
                    {/* Duration */}
                    <div className="space-y-2">
                        <Label htmlFor="duration" className="text-xs font-bold text-muted-foreground uppercase flex items-center gap-2">
                            <Clock className="h-3 w-3" />
                            Duration
                        </Label>
                        <Input
                            id="duration"
                            placeholder="e.g. 2.5 Hours"
                            value={metadata.duration}
                            onChange={(e) => setMetadata({ duration: e.target.value })}
                            className="bg-card"
                        />
                    </div>

                    {/* Instructions */}
                    <div className="space-y-2">
                        <Label htmlFor="instructions" className="text-xs font-bold text-muted-foreground uppercase">General Instructions</Label>
                        <Textarea
                            id="instructions"
                            placeholder="Enter student instructions..."
                            value={metadata.instructions}
                            onChange={(e) => setMetadata({ instructions: e.target.value })}
                            className="bg-card min-h-[100px]"
                        />
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
