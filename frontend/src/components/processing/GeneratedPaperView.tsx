/**
 * components/processing/GeneratedPaperView.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Displays the formatted generated question paper after processing completes.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { FileText, Award, BookOpen, Brain } from "lucide-react";
import type { DraftPaper } from "@/types/api";

interface GeneratedPaperViewProps {
    paper: DraftPaper;
}

export function GeneratedPaperView({ paper }: GeneratedPaperViewProps) {
    const stats = paper.selection_stats;

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {/* Stats Overview */}
            {stats && (
                <Card className="border-2 border-primary/20 bg-primary/5">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-lg">
                            <Award className="h-5 w-5 text-primary" />
                            Paper Statistics
                        </CardTitle>
                        <CardDescription>Generated question paper summary</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground">Total Questions</p>
                                <p className="text-2xl font-bold">{stats.total_questions}</p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground">PYQ Exact Match</p>
                                <p className="text-2xl font-bold text-green-600">{stats.pyq_exact_match}</p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground">PYQ Rephrased</p>
                                <p className="text-2xl font-bold text-blue-600">
                                    {stats.pyq_rephrased_marks + stats.pyq_rephrased_bloom}
                                </p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground">Generated New</p>
                                <p className="text-2xl font-bold text-purple-600">{stats.generated_new}</p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground">Direct Generated</p>
                                <p className="text-2xl font-bold text-amber-600">{stats.direct_generated}</p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground">PYQ Usage</p>
                                <p className="text-2xl font-bold text-primary">
                                    {Math.round(
                                        ((stats.pyq_exact_match + stats.pyq_rephrased_marks + stats.pyq_rephrased_bloom) /
                                            stats.total_questions) *
                                            100
                                    )}
                                    %
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Question Paper Sections */}
            {paper.sections.map((section, sIdx) => (
                <Card key={sIdx} className="overflow-hidden">
                    <CardHeader className="bg-muted/30">
                        <CardTitle className="flex items-center gap-2">
                            <FileText className="h-5 w-5" />
                            {section.section_name}
                        </CardTitle>
                        <CardDescription>{section.section_description}</CardDescription>
                    </CardHeader>
                    <CardContent className="pt-6">
                        <div className="space-y-8">
                            {section.questions.map((q, qIdx) => (
                                <div key={qIdx} className="space-y-3">
                                    {/* Question Header */}
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 flex-wrap mb-2">
                                                <Badge variant="outline" className="font-mono text-xs">
                                                    Q{q.question_number}
                                                </Badge>
                                                <Badge variant="secondary" className="text-xs">
                                                    {q.marks} marks
                                                </Badge>
                                                <Badge
                                                    variant="outline"
                                                    className="text-xs flex items-center gap-1"
                                                >
                                                    <Brain className="h-3 w-3" />
                                                    {q.bloom_level}
                                                </Badge>
                                                <Badge
                                                    variant="outline"
                                                    className="text-xs flex items-center gap-1"
                                                >
                                                    <BookOpen className="h-3 w-3" />
                                                    {q.module}
                                                </Badge>
                                            </div>
                                            <div className="text-xs text-muted-foreground space-y-0.5">
                                                <p>
                                                    <span className="font-medium">Topic:</span> {q.topic}
                                                </p>
                                                {q.subtopic && (
                                                    <p>
                                                        <span className="font-medium">Subtopic:</span> {q.subtopic}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                        <Badge
                                            variant={
                                                q.selection_method === "pyq_exact"
                                                    ? "default"
                                                    : q.selection_method.includes("rephrased")
                                                    ? "secondary"
                                                    : "outline"
                                            }
                                            className="text-xs shrink-0"
                                        >
                                            {q.selection_method === "pyq_exact"
                                                ? "📌 PYQ"
                                                : q.selection_method.includes("rephrased")
                                                ? "🔄 Rephrased"
                                                : "✨ Generated"}
                                        </Badge>
                                    </div>

                                    {/* Question Text */}
                                    <div className="pl-4 border-l-2 border-muted-foreground/20">
                                        <p className="text-sm leading-relaxed whitespace-pre-wrap">
                                            {q.question_text}
                                        </p>
                                    </div>

                                    {/* Source Info */}
                                    {q.source_pyq_id && (
                                        <p className="text-xs text-muted-foreground italic pl-4">
                                            Source: PYQ ID {q.source_pyq_id}
                                        </p>
                                    )}

                                    {qIdx < section.questions.length - 1 && (
                                        <Separator className="mt-6 opacity-50" />
                                    )}
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}
