"use client";

import React from "react";
import {
    Download,
    Printer,
    Copy,
    Save,
    RefreshCw,
    FileText,
    ChevronDown
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

// 📄 SAMPLE DATA
interface QuestionSection {
    title: string;
    instructions: string;
    questions: string[];
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
                "Define Intelligent Agent.",
                "Explain PEAS description.",
                "What is Bayesian Network?",
                "State the purpose of GAN."
            ]
        },
        {
            title: "Section B",
            instructions: "Answer any 5 questions. Each carries 6 marks.",
            questions: [
                "Explain GAN architecture with diagram.",
                "Compare GAN and VAE.",
                "Discuss Hidden Markov Models.",
                "Explain Transfer Learning techniques.",
                "Describe XGBoost algorithm."
            ]
        },
        {
            title: "Section C",
            instructions: "Answer any 2 questions. Each carries 10 marks.",
            questions: [
                "Design a GAN model for image generation.",
                "Explain ensemble learning methods in detail.",
                "Discuss emerging AI technologies."
            ]
        }
    ]
};

export default function ResultQPPage() {

    const handlePrint = () => {
        window.print();
    };

    const handleCopy = () => {
        let text = `${EXAM_DATA.examTitle}\n`;
        text += `Subject: ${EXAM_DATA.subject}\n`;
        text += `Grade: ${EXAM_DATA.grade} | Duration: ${EXAM_DATA.duration} | Total Marks: ${EXAM_DATA.totalMarks}\n`;
        text += `--------------------------------------------------\n\n`;

        EXAM_DATA.sections.forEach((section) => {
            text += `${section.title.toUpperCase()}\n`;
            text += `Instructions: ${section.instructions}\n\n`;
            section.questions.forEach((q, i) => {
                text += `${i + 1}. ${q}\n`;
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
        <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 font-body antialiased selection:bg-primary/10">

            {/* 1️⃣ TOP ACTION BAR (Sticky) */}
            <div className="sticky top-0 z-[100] w-full border-b border-border/50 bg-background/80 backdrop-blur-md print:hidden">
                <div className="container mx-auto max-w-5xl h-16 flex items-center justify-between px-6">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white font-black italic shadow-sm">Q</div>
                        <span className="text-sm font-black uppercase tracking-tighter italic text-foreground">Result Preview</span>
                    </div>

                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="sm" onClick={handleCopy} className="text-xs font-bold gap-2 uppercase tracking-widest hover:bg-primary/5 hover:text-primary transition-colors">
                            <Copy className="h-3.5 w-3.5" />
                            Copy Text
                        </Button>

                        <Separator orientation="vertical" className="h-6 opacity-30" />

                        <Button variant="ghost" size="sm" onClick={handleSave} className="text-xs font-bold gap-2 uppercase tracking-widest hover:bg-green-500/5 hover:text-green-600 transition-colors">
                            <Save className="h-3.5 w-3.5" />
                            Save
                        </Button>

                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="secondary" size="sm" className="text-xs font-bold gap-2 uppercase tracking-widest shadow-sm">
                                    <Download className="h-3.5 w-3.5" />
                                    Download
                                    <ChevronDown className="h-3.5 w-3.5 opacity-50" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-48">
                                <DropdownMenuItem onClick={handlePrint} className="gap-2 font-bold cursor-pointer">
                                    <FileText className="h-4 w-4 text-rose-500" />
                                    PDF (via Print)
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => toast.info("Exporting to DOCX...")} className="gap-2 font-bold cursor-pointer">
                                    <FileText className="h-4 w-4 text-blue-500" />
                                    Word Document
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>

                        <Button size="sm" onClick={handlePrint} className="bg-zinc-900 dark:bg-zinc-100 dark:text-zinc-950 text-white text-xs font-bold gap-2 uppercase tracking-widest shadow-lg hover:scale-105 transition-all">
                            <Printer className="h-3.5 w-3.5" />
                            Print Paper
                        </Button>
                    </div>
                </div>
            </div>

            {/* 2️⃣ QUESTION PAPER LAYOUT */}
            <main className="container mx-auto py-12 px-6 flex justify-center print:p-0 print:m-0 print:block">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className={cn(
                        "w-full max-w-[800px] bg-white dark:bg-zinc-900 border border-border shadow-2xl p-12 md:p-20 relative overflow-hidden font-serif",
                        "print:shadow-none print:border-none print:p-0 print:m-0 print:max-w-none print:text-black print:bg-white"
                    )}
                >
                    {/* Header Section */}
                    <header className="text-center mb-12">
                        <h1 className="text-2xl md:text-3xl font-black uppercase tracking-tight mb-2">
                            {EXAM_DATA.examTitle}
                        </h1>
                        <div className="h-1 w-24 bg-zinc-900 dark:bg-white mx-auto mb-8 rounded-full print:bg-black" />

                        <div className="grid grid-cols-2 gap-y-4 text-sm font-bold uppercase tracking-widest text-zinc-600 dark:text-zinc-400 print:text-black">
                            <div className="text-left border-b border-border pb-2 inline-block">
                                Subject: <span className="text-zinc-950 dark:text-white print:text-black">{EXAM_DATA.subject}</span>
                            </div>
                            <div className="text-right border-b border-border pb-2 inline-block">
                                Grade/Year: <span className="text-zinc-950 dark:text-white print:text-black">{EXAM_DATA.grade}</span>
                            </div>
                            <div className="text-left border-b border-border pb-2 inline-block">
                                Duration: <span className="text-zinc-950 dark:text-white print:text-black">{EXAM_DATA.duration}</span>
                            </div>
                            <div className="text-right border-b border-border pb-2 inline-block">
                                Total Marks: <span className="text-zinc-950 dark:text-white print:text-black">{EXAM_DATA.totalMarks}</span>
                            </div>
                        </div>
                    </header>

                    <Separator className="mb-12 opacity-50" />

                    {/* 3️⃣ SECTIONS RENDERING */}
                    <div className="space-y-12">
                        {EXAM_DATA.sections.map((section, sIdx) => (
                            <div key={sIdx} className="space-y-6">
                                <div className="flex items-center gap-4">
                                    <h2 className="text-lg font-black uppercase tracking-widest border-l-4 border-primary pl-4 print:border-black">
                                        {section.title}
                                    </h2>
                                </div>

                                <p className="text-sm italic font-medium text-zinc-500 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-800/50 p-3 rounded-lg border-l-2 border-border print:bg-white print:text-black print:border-l-2 print:border-zinc-200">
                                    {section.instructions}
                                </p>

                                <ol className="space-y-4">
                                    {section.questions.map((question, qIdx) => (
                                        <li key={qIdx} className="flex gap-4 group">
                                            <span className="font-bold tabular-nums text-zinc-400 print:text-black">{qIdx + 1}.</span>
                                            <p className="text-md leading-relaxed font-medium flex-1 print:text-black">
                                                {question}
                                            </p>
                                            <div className="opacity-0 group-hover:opacity-100 transition-opacity print:hidden">
                                                <Button variant="ghost" size="icon" className="h-6 w-6">
                                                    <RefreshCw className="h-3 w-3" />
                                                </Button>
                                            </div>
                                        </li>
                                    ))}
                                </ol>
                            </div>
                        ))}
                    </div>

                    <footer className="mt-24 pt-12 border-t border-border/30 text-center opacity-30 print:hidden">
                        <p className="text-[10px] uppercase font-black tracking-[0.5em] text-foreground">Generated by QPilot AI System</p>
                    </footer>
                </motion.div>
            </main>
        </div>
    );
}
