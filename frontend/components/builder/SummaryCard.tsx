"use client";

/**
 * components/builder/SummaryCard.tsx
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
    ChartContainer,
    ChartTooltip,
    ChartTooltipContent,
    type ChartConfig
} from "@/components/ui/chart";
import { Pie, PieChart, Cell, ResponsiveContainer } from "recharts";
import {
    TrendingUp,
    FileCheck,
    BarChart3,
    Target,
    AlertCircle,
    HelpCircle
} from "lucide-react";
import type { Section, Project } from "@/types/api";

interface SummaryCardProps {
    project: Project | null;
    sections: Section[];
    isLoading: boolean;
}

const COLORS = ["#2563eb", "#10b981", "#8b5cf6", "#f59e0b", "#ef4444"];

export function SummaryCard({ project, sections, isLoading }: SummaryCardProps) {
    if (isLoading || !project) {
        return (
            <Card className="h-full shadow-sm border-border/60">
                <CardContent className="pt-6 space-y-4">
                    <div className="h-32 w-full bg-muted animate-pulse rounded-xl" />
                    <div className="h-4 w-full bg-muted animate-pulse rounded" />
                    <div className="h-4 w-2/3 bg-muted animate-pulse rounded" />
                </CardContent>
            </Card>
        );
    }

    const totalSectionMarks = sections.reduce((sum, s) => sum + s.totalMarks, 0);
    const totalQuestions = sections.reduce((sum, s) => sum + s.numQuestions, 0);
    const markCompletion = Math.min(100, (totalSectionMarks / project.totalMarks) * 100);
    const isMarksValid = totalSectionMarks === project.totalMarks;

    // Prepare data for distribution chart
    const chartData = sections.map((s, i) => ({
        name: s.name,
        value: s.totalMarks,
        fill: COLORS[i % COLORS.length]
    }));

    const chartConfig = {
        value: { label: "Marks" },
        ...Object.fromEntries(sections.map((s, i) => [s.name, { label: s.name, color: COLORS[i % COLORS.length] }]))
    } satisfies ChartConfig;

    // Difficulty breakdown
    const difficultyCount = {
        easy: sections.filter(s => s.difficulty === "easy").reduce((sum, s) => sum + s.totalMarks, 0),
        medium: sections.filter(s => s.difficulty === "medium").reduce((sum, s) => sum + s.totalMarks, 0),
        hard: sections.filter(s => s.difficulty === "hard").reduce((sum, s) => sum + s.totalMarks, 0),
    };

    return (
        <Card className="h-full shadow-sm border-border/60 flex flex-col bg-card/50">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-primary" />
                    Live Paper Summary
                </CardTitle>
                <CardDescription className="text-xs">Dynamic analysis of your paper structure.</CardDescription>
            </CardHeader>

            <CardContent className="flex-1 space-y-6 pt-4">
                {/* Status Check */}
                <div className={`p-3 rounded-lg border flex items-start gap-3 ${isMarksValid ? "bg-green-50 border-green-200 dark:bg-green-950/20 dark:border-green-800/30" : "bg-amber-50 border-amber-200 dark:bg-amber-950/20 dark:border-amber-800/30"}`}>
                    {isMarksValid ? (
                        <FileCheck className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
                    ) : (
                        <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400 mt-0.5" />
                    )}
                    <div className="space-y-1">
                        <p className={`text-xs font-bold ${isMarksValid ? "text-green-800 dark:text-green-300" : "text-amber-800 dark:text-amber-300"}`}>
                            {isMarksValid ? "Validation Passed" : "Marks Mismatch"}
                        </p>
                        <p className="text-[10px] text-muted-foreground leading-tight">
                            {isMarksValid
                                ? "Total section marks match the target."
                                : `Target: ${project.totalMarks}, Current: ${totalSectionMarks}. Difference: ${project.totalMarks - totalSectionMarks}`}
                        </p>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1 text-center p-3 rounded-xl bg-background border border-border/50">
                        <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Total Marks</p>
                        <p className="text-xl font-bold text-foreground">{totalSectionMarks}<span className="text-xs text-muted-foreground font-normal"> / {project.totalMarks}</span></p>
                    </div>
                    <div className="space-y-1 text-center p-3 rounded-xl bg-background border border-border/50">
                        <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Total Qs</p>
                        <p className="text-xl font-bold text-foreground">{totalQuestions}</p>
                    </div>
                </div>

                {/* Mark Completion Progress */}
                <div className="space-y-2">
                    <div className="flex justify-between text-[11px] font-medium">
                        <span className="text-muted-foreground">Allocation Progress</span>
                        <span className={isMarksValid ? "text-green-600" : "text-primary"}>{Math.round(markCompletion)}%</span>
                    </div>
                    <Progress value={markCompletion} className="h-1.5" />
                </div>

                <Separator className="opacity-50" />

                {/* Marks Distribution Chart */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2">
                        <TrendingUp className="h-3.5 w-3.5 text-blue-500" />
                        <span className="text-xs font-semibold">Marks Distribution</span>
                    </div>

                    <div className="h-[160px] w-full mt-2">
                        <ChartContainer config={chartConfig} className="mx-auto aspect-square h-full">
                            <PieChart>
                                <ChartTooltip cursor={false} content={<ChartTooltipContent hideLabel />} />
                                <Pie
                                    data={chartData}
                                    dataKey="value"
                                    nameKey="name"
                                    innerRadius={50}
                                    outerRadius={70}
                                    strokeWidth={5}
                                >
                                    {chartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.fill} />
                                    ))}
                                </Pie>
                            </PieChart>
                        </ChartContainer>
                    </div>
                </div>

                {/* Difficulty Breakdown */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2">
                        <Target className="h-3.5 w-3.5 text-amber-500" />
                        <span className="text-xs font-semibold">Difficulty Breakdown</span>
                    </div>

                    <div className="space-y-2.5 mt-2">
                        <div className="space-y-1">
                            <div className="flex justify-between text-[10px] uppercase tracking-tighter font-bold">
                                <span className="text-green-600">Easy</span>
                                <span>{difficultyCount.easy}m</span>
                            </div>
                            <Progress value={(difficultyCount.easy / totalSectionMarks) * 100 || 0} className="h-1 bg-muted" />
                        </div>
                        <div className="space-y-1">
                            <div className="flex justify-between text-[10px] uppercase tracking-tighter font-bold">
                                <span className="text-amber-600">Medium</span>
                                <span>{difficultyCount.medium}m</span>
                            </div>
                            <Progress value={(difficultyCount.medium / totalSectionMarks) * 100 || 0} className="h-1 bg-muted" />
                        </div>
                        <div className="space-y-1">
                            <div className="flex justify-between text-[10px] uppercase tracking-tighter font-bold">
                                <span className="text-red-600">Hard</span>
                                <span>{difficultyCount.hard}m</span>
                            </div>
                            <Progress value={(difficultyCount.hard / totalSectionMarks) * 100 || 0} className="h-1 bg-muted" />
                        </div>
                    </div>
                </div>
            </CardContent>

            <CardFooter className="pt-2 border-t bg-muted/20">
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground w-full">
                    <HelpCircle className="h-3 w-3" />
                    <span>Generated from current active sections.</span>
                </div>
            </CardFooter>
        </Card>
    );
}
