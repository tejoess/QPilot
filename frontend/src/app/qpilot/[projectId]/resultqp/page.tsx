"use client";

import React, { useMemo } from "react";
import {
    Download,
    Printer,
    Copy,
    Save,
    RefreshCw,
    RotateCcw,
    FileText,
    ChevronDown,
    LayoutDashboard,
    ArrowLeft
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { QPilotSidebar } from "@/components/qpilot/QPilotSidebar";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useOrchestrationStore } from "@/store/orchestrationStore";
import { useQPilotStore } from "@/store/qpilotStore";

interface Question {
    text: string;
    marks: number;
    bloom?: string;
}

interface QuestionSection {
    title: string;
    instructions: string;
    questions: Question[];
}

interface ExamPaper {
    examTitle: string;
    subject: string;
    grade: string;
    totalMarks: number;
    duration: string;
    sections: QuestionSection[];
}

const EXAM_DATA: ExamPaper = {
    examTitle: "Midterm Examination",
    subject: "Artificial Intelligence",
    grade: "Semester 7",
    totalMarks: 80,
    duration: "3 Hours",
    sections: [
        {
            title: "Section A",
            instructions: "Answer all questions. Each question carries 2 marks.",
            questions: [
                { text: "Define Intelligent Agent.", marks: 2 },
                { text: "Explain PEAS description.", marks: 2 },
                { text: "What is Bayesian Network?", marks: 2 },
                { text: "State the purpose of GAN.", marks: 2 }
            ]
        },
        {
            title: "Section B",
            instructions: "Answer any 5 questions. Each carries 6 marks.",
            questions: [
                { text: "Explain GAN architecture with diagram.", marks: 6 },
                { text: "Compare GAN and VAE.", marks: 6 },
                { text: "Discuss Hidden Markov Models.", marks: 6 },
                { text: "Explain Transfer Learning techniques.", marks: 6 },
                { text: "Describe XGBoost algorithm.", marks: 6 }
            ]
        },
        {
            title: "Section C",
            instructions: "Answer any 2 questions. Each carries 10 marks.",
            questions: [
                { text: "Design a GAN model for image generation.", marks: 10 },
                { text: "Explain ensemble learning methods in detail.", marks: 10 },
                { text: "Discuss emerging AI technologies.", marks: 10 }
            ]
        }
    ]
};

export default function ResultQPPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const router = useRouter();
    const { paperData, reset } = useOrchestrationStore();
    const { currentMetadata } = useQPilotStore();

    // Build exam paper from real backend data, fall back to sample data
    const examPaper: ExamPaper = useMemo(() => {
        if (paperData && Array.isArray(paperData.sections) && paperData.sections.length > 0) {
            const totalMarks = (paperData.sections as any[]).reduce(
                (sum: number, s: any) =>
                    sum + (s.questions as any[]).reduce((qs: number, q: any) => qs + (q.marks || 0), 0),
                0
            );
            return {
                examTitle: currentMetadata?.examTitle || "Question Paper",
                subject: currentMetadata?.subject || "—",
                grade: currentMetadata?.grade || "—",
                totalMarks: currentMetadata?.totalMarks || totalMarks,
                duration: currentMetadata?.duration || "3 Hours",
                sections: (paperData.sections as any[]).map((s: any) => ({
                    title: s.section_name || "Section",
                    instructions: s.section_description || "",
                    questions: (s.questions as any[]).map((q: any) => ({
                        text: q.question_text || "",
                        marks: q.marks || 0,
                        bloom: q.bloom_level || "",
                    })),
                })),
            };
        }
        return EXAM_DATA;
    }, [paperData, currentMetadata]);

    const handleStartOver = () => {
        reset();
        router.push(`/qpilot/${projectId}`);
        toast.info("Process reset. Ready for a new paper.");
    };

    const handlePrint = () => {
        window.print();
    };

    const handleCopy = () => {
        let text = `${examPaper.examTitle}\n`;
        text += `Subject: ${examPaper.subject}\n`;
        text += `Grade: ${examPaper.grade} | Duration: ${examPaper.duration} | Total Marks: ${examPaper.totalMarks}\n`;
        text += `--------------------------------------------------\n\n`;

        examPaper.sections.forEach((section) => {
            text += `${section.title.toUpperCase()}\n`;
            text += `Instructions: ${section.instructions}\n\n`;
            section.questions.forEach((q, i) => {
                text += `${i + 1}. ${q.text}${q.marks ? ` [${q.marks} marks]` : ""}\n`;
            });
            text += `\n`;
        });

        navigator.clipboard.writeText(text);
        toast.success("Copied successfully");
    };

    const handleSave = () => {
        console.log("Saving paper to backend...");
        toast.info("Saving paper... (Simulated)");
        setTimeout(() => toast.success("Paper saved to your projects"), 1000);
    };

    return (
        <SidebarProvider style={{
            "--sidebar-width": "240px",
            "--sidebar-width-icon": "70px"
        } as React.CSSProperties}>
            <div className="flex h-screen w-full bg-background overflow-hidden selection:bg-primary/10 print:h-auto print:overflow-visible">
                {/* 1. SIDEBAR */}
                <div className="print:hidden">
                    <QPilotSidebar />
                </div>

                <SidebarInset className="flex-1 overflow-hidden bg-zinc-50 dark:bg-zinc-950 print:overflow-visible print:h-auto print:bg-white">
                    <div className="flex h-full overflow-hidden print:h-auto print:overflow-visible">

                        {/* 2. LEFT ACTION PANEL (Replaces Top Navbar) */}
                        <div className="w-[360px] border-r border-border/50 bg-white dark:bg-zinc-900/50 overflow-hidden flex flex-col print:hidden">
                            <div className="p-6 border-b border-border/50 bg-background/50 space-y-4">
                                <Link href={`/qpilot/${projectId}`} className="flex items-center gap-2 text-xs font-bold text-muted-foreground hover:text-primary transition-colors uppercase tracking-widest">
                                    <ArrowLeft className="h-3 w-3" />
                                    Back to Editor
                                </Link>
                                <div className="space-y-1">
                                    <h2 className="text-lg font-black uppercase tracking-tight text-foreground flex items-center gap-2">
                                        <div className="w-6 h-6 rounded-md bg-primary flex items-center justify-center text-white text-[10px] font-black italic">Q</div>
                                        Result Preview
                                    </h2>
                                    <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">Post-Generation Controls</p>
                                </div>
                            </div>

                            <div className="flex-1 overflow-y-auto p-6 space-y-8">
                                {/* PRIMARY ACTIONS */}
                                <div className="space-y-3">
                                    <span className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/50">Primary Actions</span>
                                    <Button onClick={handlePrint} className="w-full h-12 bg-zinc-900 dark:bg-zinc-100 dark:text-zinc-950 text-white font-bold gap-3 uppercase tracking-widest shadow-xl hover:scale-[1.02] transition-all">
                                        <Printer className="h-4 w-4" />
                                        Print Question Paper
                                    </Button>

                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="outline" className="w-full h-12 font-bold gap-3 uppercase tracking-widest border-2">
                                                <Download className="h-4 w-4" />
                                                Export Options
                                                <ChevronDown className="h-4 w-4 ml-auto opacity-50" />
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="center" className="w-[312px] p-2">
                                            <DropdownMenuItem onClick={handlePrint} className="h-11 gap-3 font-bold cursor-pointer rounded-lg hover:bg-rose-50 dark:hover:bg-rose-500/10">
                                                <FileText className="h-4 w-4 text-rose-500" />
                                                Download as PDF
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => toast.info("Exporting to DOCX...")} className="h-11 gap-3 font-bold cursor-pointer rounded-lg hover:bg-blue-50 dark:hover:bg-blue-500/10">
                                                <FileText className="h-4 w-4 text-blue-500" />
                                                Download as Word (.docx)
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </div>

                                <Separator className="opacity-50" />

                                {/* UTILITIES */}
                                <div className="space-y-3">
                                    <span className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/50">Utilities</span>
                                    <Button variant="ghost" onClick={handleCopy} className="w-full justify-start h-11 px-4 font-bold gap-3 uppercase tracking-widest hover:bg-primary/5 hover:text-primary transition-all">
                                        <Copy className="h-4 w-4" />
                                        Copy Plain Text
                                    </Button>

                                    <Button variant="ghost" onClick={handleSave} className="w-full justify-start h-11 px-4 font-bold gap-3 uppercase tracking-widest hover:bg-green-500/5 hover:text-green-600 transition-all">
                                        <Save className="h-4 w-4" />
                                        Save to Projects
                                    </Button>

                                    <div className="pt-4">
                                        <Button 
                                            variant="outline" 
                                            onClick={handleStartOver} 
                                            className="w-full justify-start h-11 px-4 font-bold gap-3 uppercase tracking-widest border-2 hover:bg-destructive/10 hover:text-destructive hover:border-destructive transition-all"
                                        >
                                            <RotateCcw className="h-4 w-4" />
                                            Start Over
                                        </Button>
                                    </div>
                                </div>

                                {/* DOC INFO */}
                                <div className="pt-8 mt-auto">
                                    <div className="p-4 rounded-xl bg-muted/50 border border-border/50">
                                        <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/60 block mb-2">Document Metadata</span>
                                        <div className="space-y-1.5">
                                            <div className="flex justify-between text-[11px] font-bold uppercase">
                                                <span className="text-muted-foreground">ID:</span>
                                                <span className="text-foreground truncate ml-4">{projectId}</span>
                                            </div>
                                            <div className="flex justify-between text-[11px] font-bold uppercase">
                                                <span className="text-muted-foreground">Status:</span>
                                                <span className="text-green-500">Validated</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* 3. MAIN PREVIEW AREA */}
                        <main className="flex-1 overflow-y-auto bg-zinc-100/50 dark:bg-zinc-950/50 p-8 md:p-12 print:p-0 print:bg-white custom-scrollbar-thin print:overflow-visible">
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.5 }}
                                className={cn(
                                    "mx-auto w-full max-w-[800px] bg-white dark:bg-zinc-900 border border-border/80 shadow-2xl p-12 md:p-20 relative overflow-hidden font-serif",
                                    "print:shadow-none print:border-none print:p-0 print:m-0 print:max-w-none print:text-black print:bg-white"
                                )}
                            >
                                {/* Paper Header */}
                                <header className="text-center mb-12">
                                    <h1 
                                        className="text-2xl md:text-3xl font-black uppercase tracking-tight mb-2 text-zinc-900 dark:text-zinc-100 print:text-black outline-none focus:ring-2 focus:ring-primary/20 rounded px-2"
                                        contentEditable
                                        suppressContentEditableWarning
                                    >
                                        {examPaper.examTitle}
                                    </h1>
                                    <div className="h-1.5 w-24 bg-zinc-900 dark:bg-white mx-auto mb-8 rounded-full print:bg-black" />

                                    <div className="grid grid-cols-2 gap-y-4 text-[13px] font-bold uppercase tracking-widest text-zinc-600 dark:text-zinc-400 print:text-black">
                                        <div className="text-left border-b border-zinc-100 dark:border-zinc-800 pb-2 inline-block">
                                            Subject: <span className="text-zinc-950 dark:text-zinc-200 print:text-black outline-none" contentEditable suppressContentEditableWarning>{examPaper.subject}</span>
                                        </div>
                                        <div className="text-right border-b border-zinc-100 dark:border-zinc-800 pb-2 inline-block">
                                            Grade/Year: <span className="text-zinc-950 dark:text-zinc-200 print:text-black outline-none" contentEditable suppressContentEditableWarning>{examPaper.grade}</span>
                                        </div>
                                        <div className="text-left border-b border-zinc-100 dark:border-zinc-800 pb-2 inline-block">
                                            Duration: <span className="text-zinc-950 dark:text-zinc-200 print:text-black outline-none" contentEditable suppressContentEditableWarning>{examPaper.duration}</span>
                                        </div>
                                        <div className="text-right border-b border-zinc-100 dark:border-zinc-800 pb-2 inline-block">
                                            Total Marks: <span className="text-zinc-950 dark:text-zinc-200 print:text-black outline-none" contentEditable suppressContentEditableWarning>{examPaper.totalMarks}</span>
                                        </div>
                                    </div>
                                </header>

                                <Separator className="mb-12 opacity-30" />

                                {/* SECTIONS */}
                                <div className="space-y-12">
                                    {examPaper.sections.map((section, sIdx) => (
                                        <div key={sIdx} className="space-y-6">
                                            <div className="flex items-center gap-4">
                                                <h2 
                                                    className="text-lg font-black uppercase tracking-widest border-l-[6px] border-primary pl-4 print:border-black text-zinc-900 dark:text-zinc-100 outline-none focus:ring-2 focus:ring-primary/20 rounded"
                                                    contentEditable
                                                    suppressContentEditableWarning
                                                >
                                                    {section.title}
                                                </h2>
                                            </div>

                                            <p 
                                                className="text-sm italic font-medium text-zinc-500 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-800/40 p-4 rounded-xl border-l-2 border-zinc-200 dark:border-zinc-700 print:bg-white print:text-black print:border-zinc-200 outline-none focus:ring-2 focus:ring-primary/20"
                                                contentEditable
                                                suppressContentEditableWarning
                                            >
                                                {section.instructions}
                                            </p>

                                            <ol className="space-y-6">
                                                {section.questions.map((question, qIdx) => (
                                                    <li key={qIdx} className="flex gap-4 group">
                                                        <span className="font-bold tabular-nums text-zinc-400 print:text-black text-sm">{qIdx + 1}.</span>
                                                        <p 
                                                            className="text-[17px] leading-relaxed font-medium flex-1 text-zinc-800 dark:text-zinc-200 print:text-black outline-none focus:ring-2 focus:ring-primary/20 rounded p-1 -m-1"
                                                            contentEditable
                                                            suppressContentEditableWarning
                                                        >
                                                            {question.text}
                                                        </p>
                                                        {question.marks > 0 && (
                                                            <span className="text-[11px] font-black text-zinc-400 dark:text-zinc-500 tabular-nums shrink-0 print:text-black">
                                                                [{question.marks}M]
                                                            </span>
                                                        )}
                                                        <div className="opacity-0 group-hover:opacity-100 transition-opacity print:hidden">
                                                            <Button variant="ghost" size="icon" className="h-7 w-7 rounded-full hover:bg-primary/10 hover:text-primary">
                                                                <RefreshCw className="h-3.5 w-3.5" />
                                                            </Button>
                                                        </div>
                                                    </li>
                                                ))}
                                            </ol>
                                        </div>
                                    ))}
                                </div>

                                <footer className="mt-24 pt-12 border-t border-border/20 text-center opacity-30 print:hidden">
                                    <p className="text-[10px] uppercase font-black tracking-[0.5em] text-zinc-500 dark:text-zinc-400">Generated by QPilot AI System</p>
                                </footer>
                            </motion.div>
                        </main>
                    </div>
                </SidebarInset>
            </div>
        </SidebarProvider>
    );
}
