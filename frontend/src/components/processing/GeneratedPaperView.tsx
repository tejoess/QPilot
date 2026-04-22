"use client";

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
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import type { DraftPaper, GDTBlock, GDTTableContent, GDTPlotContent, GDTGraphContent } from "@/types/api";

// ─────────────────────────────────────────────────────────────
// GDT sub-renderers
// ─────────────────────────────────────────────────────────────

function GDTTableRenderer({ content }: { content: GDTTableContent }) {
    return (
        <div className="overflow-x-auto my-2">
            <table className="text-xs border-collapse w-full">
                <thead>
                    <tr>
                        {content.headers.map((h, i) => (
                            <th key={i} className="border border-border bg-muted px-3 py-1.5 text-left font-semibold">
                                {h}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {content.rows.map((row, ri) => (
                        <tr key={ri} className="even:bg-muted/30">
                            {row.map((cell, ci) => (
                                <td key={ci} className="border border-border px-3 py-1.5 min-w-[60px]">
                                    {String(cell)}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function GDTPlotRenderer({ content }: { content: GDTPlotContent }) {
    const data = content.x.map((xv, i) => ({ x: xv, y: content.y[i] ?? 0 }));
    return (
        <div className="my-2">
            {content.title && (
                <p className="text-[11px] font-semibold text-muted-foreground mb-1">{content.title}</p>
            )}
            <ResponsiveContainer width="100%" height={180}>
                <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="x" label={{ value: content.xlabel || "x", position: "insideBottom", offset: -2, fontSize: 10 }} tick={{ fontSize: 10 }} />
                    <YAxis label={{ value: content.ylabel || "y", angle: -90, position: "insideLeft", fontSize: 10 }} tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="y" stroke="hsl(var(--primary))" dot={{ r: 3 }} strokeWidth={2} />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}

function GDTGraphRenderer({ content }: { content: GDTGraphContent }) {
    // Render as an edge list table — actual graph image is in PDF/DOCX
    return (
        <div className="my-2 space-y-1">
            <p className="text-[11px] font-semibold text-muted-foreground">
                Graph ({content.directed ? "Directed" : "Undirected"}) — edge list:
            </p>
            <div className="overflow-x-auto">
                <table className="text-xs border-collapse">
                    <thead>
                        <tr>
                            <th className="border border-border bg-muted px-2 py-1">From</th>
                            <th className="border border-border bg-muted px-2 py-1">To</th>
                            {content.edge_labels && <th className="border border-border bg-muted px-2 py-1">Weight</th>}
                        </tr>
                    </thead>
                    <tbody>
                        {content.edges.map(([from, to], ei) => {
                            const labelKey = Object.keys(content.edge_labels || {}).find(k =>
                                k.includes(`"${from}"`) && k.includes(`"${to}"`)
                            );
                            return (
                                <tr key={ei} className="even:bg-muted/30">
                                    <td className="border border-border px-2 py-1">{from}</td>
                                    <td className="border border-border px-2 py-1">{to}</td>
                                    {content.edge_labels && (
                                        <td className="border border-border px-2 py-1">
                                            {labelKey ? String(content.edge_labels[labelKey]) : "—"}
                                        </td>
                                    )}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
            <p className="text-[10px] text-muted-foreground italic">Full graph diagram rendered in PDF/DOCX download.</p>
        </div>
    );
}

function GDTRenderer({ blocks }: { blocks: GDTBlock[] }) {
    if (!blocks || blocks.length === 0) return null;
    return (
        <div className="mt-2 space-y-2 pl-4 border-l-2 border-primary/30">
            {blocks.map((block, idx) => {
                if (block.type === "table") {
                    return <GDTTableRenderer key={idx} content={block.content as GDTTableContent} />;
                }
                if (block.type === "plot") {
                    return <GDTPlotRenderer key={idx} content={block.content as GDTPlotContent} />;
                }
                if (block.type === "graph_ds") {
                    return <GDTGraphRenderer key={idx} content={block.content as GDTGraphContent} />;
                }
                if (block.type === "formula") {
                    return (
                        <div key={idx} className="my-2 font-mono text-sm bg-muted/50 rounded px-3 py-1.5 inline-block">
                            {String(block.content)}
                        </div>
                    );
                }
                return null;
            })}
        </div>
    );
}

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
                                        <GDTRenderer blocks={q.gdt ?? []} />
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
