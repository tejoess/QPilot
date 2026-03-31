"use client";

import React, { useEffect, useMemo, useState } from "react";
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
    ArrowLeft,
    KeyRound,
    Loader2,
    CheckCircle2,
    AlertTriangle,
    ChevronRight,
    BookOpen,
    Tag,
    ListChecks,
    Minus,
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
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { QPilotSidebar } from "@/components/qpilot/QPilotSidebar";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useOrchestrationStore } from "@/store/orchestrationStore";
import { useQPilotStore } from "@/store/qpilotStore";
import { TemplateRenderButton } from "@/components/qpilot/TemplateRenderButton";
import { useUser } from "@clerk/nextjs";
import { BACKEND_URL } from "@/lib/projectApi";
import { getProjectPaperSnapshot } from "@/actions/dashboardActions";

// ── Types ──────────────────────────────────────────────────────────────────────

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

interface AnswerSubQuestion {
    sub_question_no: string;
    question: string;
    full_marks: number | string;
    keywords?: string[];
    expected_points?: string[];
    marking_scheme?: {
        full_marks_criteria?: string;
        partial_marks?: { marks: number | string; criteria: string }[];
        deductions?: string[];
    };
    error?: string;
}

interface AnswerQuestion {
    question_no: string;
    type: string;
    marks_each?: number | string;
    total_marks?: number | string;
    sub_questions: AnswerSubQuestion[];
}

interface AnswerKey {
    answer_key: AnswerQuestion[];
}

// ── Sample fallback data ───────────────────────────────────────────────────────

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

// ── Answer Key renderer component ──────────────────────────────────────────────

function AnswerKeyView({ data }: { data: AnswerKey }) {
    return (
        <div className="space-y-10">
            {data.answer_key.map((q, qi) => (
                <div key={qi} className="space-y-5">
                    {/* Question header */}
                    <div className="flex items-center gap-3">
                        <div className="px-3 py-1.5 rounded-lg bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-xs font-black uppercase tracking-widest">
                            {q.question_no}
                        </div>
                        {q.type && (
                            <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-widest border border-border rounded px-2 py-0.5">
                                {q.type}
                            </span>
                        )}
                        {q.total_marks && (
                            <span className="text-[11px] font-black text-emerald-600 ml-auto">
                                {q.total_marks} Marks Total
                            </span>
                        )}
                    </div>

                    {/* Sub-questions */}
                    <div className="space-y-6 pl-4 border-l-2 border-border/50">
                        {q.sub_questions.map((sq, sqi) => (
                            <motion.div
                                key={sqi}
                                initial={{ opacity: 0, y: 8 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: sqi * 0.05 }}
                                className="space-y-4 p-5 rounded-xl bg-white dark:bg-zinc-900 border border-border/60 shadow-sm"
                            >
                                {/* Sub-question header */}
                                <div className="flex items-start justify-between gap-4">
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-black text-muted-foreground">{sq.sub_question_no}</span>
                                            {sq.full_marks && (
                                                <span className="text-[10px] font-black text-primary border border-primary/30 bg-primary/5 rounded px-1.5 py-0.5">
                                                    {sq.full_marks} Marks
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-sm font-semibold text-foreground leading-snug">{sq.question}</p>
                                    </div>
                                </div>

                                {sq.error ? (
                                    <div className="flex items-center gap-2 text-destructive text-xs font-semibold p-3 bg-destructive/5 rounded-lg border border-destructive/20">
                                        <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                                        {sq.error}
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        {/* Keywords */}
                                        {sq.keywords && sq.keywords.length > 0 && (
                                            <div className="space-y-2">
                                                <div className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-rose-500">
                                                    <Tag className="h-3 w-3" />
                                                    Keywords
                                                </div>
                                                <div className="flex flex-wrap gap-1.5">
                                                    {sq.keywords.map((kw, ki) => (
                                                        <span key={ki} className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 dark:bg-rose-500/10 text-rose-600 border border-rose-200 dark:border-rose-500/20">
                                                            {kw}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Expected Points */}
                                        {sq.expected_points && sq.expected_points.length > 0 && (
                                            <div className="space-y-2">
                                                <div className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-emerald-600">
                                                    <ListChecks className="h-3 w-3" />
                                                    Expected Points
                                                </div>
                                                <ol className="space-y-1.5">
                                                    {sq.expected_points.map((pt, pi) => (
                                                        <li key={pi} className="flex gap-2 text-xs text-foreground/80 leading-snug">
                                                            <span className="font-black text-emerald-600 shrink-0">{pi + 1}.</span>
                                                            {pt}
                                                        </li>
                                                    ))}
                                                </ol>
                                            </div>
                                        )}

                                        {/* Marking Scheme */}
                                        {sq.marking_scheme && (
                                            <div className="space-y-3 pt-2 border-t border-border/40">
                                                <div className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Marking Scheme</div>

                                                {sq.marking_scheme.full_marks_criteria && (
                                                    <div className="rounded-lg overflow-hidden border border-border/60">
                                                        <div className="px-3 py-2 bg-zinc-900 dark:bg-zinc-800 text-white text-[10px] font-black uppercase tracking-widest">
                                                            Full Marks Criteria
                                                        </div>
                                                        <div className="px-3 py-2.5 bg-zinc-50 dark:bg-zinc-900/50 text-xs text-foreground/80 leading-relaxed">
                                                            {sq.marking_scheme.full_marks_criteria}
                                                        </div>
                                                    </div>
                                                )}

                                                {sq.marking_scheme.partial_marks && sq.marking_scheme.partial_marks.length > 0 && (
                                                    <div className="rounded-lg overflow-hidden border border-border/60">
                                                        <div className="grid grid-cols-[3rem_1fr] bg-zinc-900 dark:bg-zinc-800 text-white text-[10px] font-black uppercase tracking-widest">
                                                            <div className="px-3 py-2 border-r border-white/10">Marks</div>
                                                            <div className="px-3 py-2">Criteria</div>
                                                        </div>
                                                        {sq.marking_scheme.partial_marks.map((pm, pmi) => (
                                                            <div key={pmi} className={cn("grid grid-cols-[3rem_1fr] text-xs", pmi % 2 === 0 ? "bg-white dark:bg-zinc-900" : "bg-zinc-50 dark:bg-zinc-800/40")}>
                                                                <div className="px-3 py-2.5 font-black text-primary border-r border-border/40">{pm.marks}</div>
                                                                <div className="px-3 py-2.5 text-foreground/80">{pm.criteria}</div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}

                                                {sq.marking_scheme.deductions && sq.marking_scheme.deductions.length > 0 && (
                                                    <div className="space-y-1.5">
                                                        <div className="text-[10px] font-black uppercase tracking-widest text-rose-500">Deductions</div>
                                                        {sq.marking_scheme.deductions.map((d, di) => (
                                                            <div key={di} className="flex gap-2 text-xs text-foreground/70">
                                                                <Minus className="h-3 w-3 text-rose-400 shrink-0 mt-0.5" />
                                                                {d}
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </motion.div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function ResultQPPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const { user } = useUser();
    const router = useRouter();
    const { paperData, reset } = useOrchestrationStore();
    const { currentMetadata } = useQPilotStore();

    // Answer key state
    const [answerKeyStatus, setAnswerKeyStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
    const [answerKeyData, setAnswerKeyData] = useState<AnswerKey | null>(null);
    const [answerKeyPdfUrl, setAnswerKeyPdfUrl] = useState<string>("");
    const [answerKeyError, setAnswerKeyError] = useState<string>("");
    const [activeTab, setActiveTab] = useState<"paper" | "answerkey">("paper");
    const [persistedPaperData, setPersistedPaperData] = useState<any | null>(null);
    const [snapshotLoading, setSnapshotLoading] = useState<boolean>(!paperData);
    const [persistedMeta, setPersistedMeta] = useState<{
        name?: string | null;
        subject?: string | null;
        grade?: string | null;
        totalMarks?: number | null;
        duration?: string | null;
    } | null>(null);

    useEffect(() => {
        let mounted = true;
        async function loadSnapshot() {
            if (paperData) {
                setSnapshotLoading(false);
                return;
            }
            if (!projectId) {
                setSnapshotLoading(false);
                return;
            }
            try {
                const snapshot = await getProjectPaperSnapshot(projectId);
                if (!mounted || !snapshot) return;
                setPersistedPaperData(snapshot.finalPaper);
                setPersistedMeta(snapshot.project);
            } finally {
                if (mounted) setSnapshotLoading(false);
            }
        }
        loadSnapshot();
        return () => {
            mounted = false;
        };
    }, [paperData, projectId]);

    const renderPaperJson = (paperData && Array.isArray((paperData as any).sections) && (paperData as any).sections.length > 0)
        ? paperData
        : persistedPaperData;

    // Build exam paper from real backend/store data, fall back to sample data
    const examPaper: ExamPaper | null = useMemo(() => {
        const sourcePaper = renderPaperJson;

        if (sourcePaper && Array.isArray(sourcePaper.sections) && sourcePaper.sections.length > 0) {
            const totalMarks = (sourcePaper.sections as any[]).reduce(
                (sum: number, s: any) =>
                    sum + (s.questions as any[]).reduce((qs: number, q: any) => qs + (q.marks || 0), 0),
                0
            );
            return {
                examTitle: currentMetadata?.examTitle || persistedMeta?.name || "Question Paper",
                subject: currentMetadata?.subject || persistedMeta?.subject || "—",
                grade: currentMetadata?.grade || persistedMeta?.grade || "—",
                totalMarks: currentMetadata?.totalMarks || persistedMeta?.totalMarks || totalMarks,
                duration: currentMetadata?.duration || persistedMeta?.duration || "3 Hours",
                sections: (sourcePaper.sections as any[]).map((s: any) => ({
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
        if (snapshotLoading) return null;
        return EXAM_DATA;
    }, [renderPaperJson, persistedMeta, currentMetadata, snapshotLoading]);

    // ── Generate Answer Key ──────────────────────────────────────────────────

    const handleGenerateAnswerKey = async () => {
        if (!paperData) {
            toast.error("No paper data available. Please generate a paper first.");
            return;
        }
        setAnswerKeyStatus("loading");
        setAnswerKeyError("");
        setAnswerKeyData(null);

        try {
            const form = new FormData();
            form.append("paper_json", JSON.stringify(paperData));
            form.append("download_pdf", "true");
            if (user?.id) form.append("user_id", user.id);
            if (projectId) form.append("project_id", projectId);

            const res = await fetch(`${BACKEND_URL}/generate-answer-key`, {
                method: "POST",
                body: form,
            });

            if (!res.ok) {
                const errText = await res.text();
                throw new Error(errText || `HTTP ${res.status}`);
            }

            const json = await res.json();
            setAnswerKeyData(json.answer_key as AnswerKey);
            if (json.pdf_url) setAnswerKeyPdfUrl(json.pdf_url);
            setAnswerKeyStatus("done");
            setActiveTab("answerkey");
            toast.success("Answer key generated!", { description: "Switch to the Answer Key tab to view it." });
        } catch (err: any) {
            console.error(err);
            setAnswerKeyError(err.message || "Generation failed");
            setAnswerKeyStatus("error");
            toast.error("Answer key generation failed", { description: err.message });
        }
    };

    const handleDownloadAnswerKeyPdf = async () => {
        if (answerKeyPdfUrl) {
            window.open(answerKeyPdfUrl, "_blank");
            return;
        }

        if (!paperData) return;
        toast.info("Preparing PDF, please wait…");
        try {
            const form = new FormData();
            form.append("paper_json", JSON.stringify(paperData));
            form.append("download_pdf", "true");
            if (user?.id) form.append("user_id", user.id);
            if (projectId) form.append("project_id", projectId);

            const res = await fetch(`${BACKEND_URL}/generate-answer-key`, {
                method: "POST",
                body: form
            });

            if (!res.ok) throw new Error(await res.text());
            const json = await res.json();
            if (json.pdf_url) {
                setAnswerKeyPdfUrl(json.pdf_url);
                window.open(json.pdf_url, "_blank");
            } else {
                toast.error("No PDF URL returned from server");
            }
        } catch (err: any) {
            toast.error("PDF download failed", { description: err.message });
        }
    };

    const handleStartOver = () => {
        reset();
        router.push(`/qpilot/${projectId}`);
        toast.info("Process reset. Ready for a new paper.");
    };

    const handlePrint = () => { window.print(); };

    const handleCopy = () => {
        if (!examPaper) return;
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
        toast.info("Saving paper… (Simulated)");
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

                        {/* ════ LEFT ACTION PANEL ════ */}
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

                                {/* ── ANSWER KEY section ── */}
                                <div className="space-y-3">
                                    <span className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/50">Answer Key</span>

                                    {/* Generate button */}
                                    <button
                                        onClick={handleGenerateAnswerKey}
                                        disabled={answerKeyStatus === "loading"}
                                        className={cn(
                                            "w-full flex items-center gap-3 p-4 rounded-xl border-2 text-left transition-all group",
                                            answerKeyStatus === "done"
                                                ? "border-emerald-500/40 bg-emerald-500/5 hover:bg-emerald-500/10"
                                                : answerKeyStatus === "error"
                                                    ? "border-destructive/30 bg-destructive/5 hover:bg-destructive/10"
                                                    : answerKeyStatus === "loading"
                                                        ? "border-primary/30 bg-primary/5 cursor-not-allowed opacity-80"
                                                        : "border-border hover:border-primary/50 hover:bg-primary/5"
                                        )}
                                    >
                                        <div className={cn(
                                            "p-2 rounded-lg flex-shrink-0 transition-colors",
                                            answerKeyStatus === "done" ? "bg-emerald-500/15 text-emerald-600" :
                                            answerKeyStatus === "error" ? "bg-destructive/10 text-destructive" :
                                            answerKeyStatus === "loading" ? "bg-primary/10 text-primary" :
                                            "bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary"
                                        )}>
                                            {answerKeyStatus === "loading" ? (
                                                <Loader2 className="h-5 w-5 animate-spin" />
                                            ) : answerKeyStatus === "done" ? (
                                                <CheckCircle2 className="h-5 w-5" />
                                            ) : answerKeyStatus === "error" ? (
                                                <AlertTriangle className="h-5 w-5" />
                                            ) : (
                                                <KeyRound className="h-5 w-5" />
                                            )}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-[13px] font-black text-foreground">
                                                {answerKeyStatus === "loading" ? "Generating…" :
                                                 answerKeyStatus === "done" ? "Answer Key Ready" :
                                                 answerKeyStatus === "error" ? "Retry Generation" :
                                                 "Generate Answer Key"}
                                            </p>
                                            <p className="text-[10px] text-muted-foreground mt-0.5">
                                                {answerKeyStatus === "loading" ? "Calling GPT-4o-mini for each question…" :
                                                 answerKeyStatus === "done" ? "Click to regenerate" :
                                                 answerKeyStatus === "error" ? answerKeyError.slice(0, 60) :
                                                 "AI-powered marking scheme & keywords"}
                                            </p>
                                        </div>
                                        {answerKeyStatus === "idle" && (
                                            <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 group-hover:text-primary transition-colors" />
                                        )}
                                    </button>

                                    {/* Download PDF button (only when answer key is ready) */}
                                    {answerKeyStatus === "done" && (
                                        <Button
                                            variant="outline"
                                            onClick={handleDownloadAnswerKeyPdf}
                                            className="w-full justify-start h-11 px-4 font-bold gap-3 uppercase tracking-widest border-2 hover:bg-emerald-500/5 hover:text-emerald-600 hover:border-emerald-500/40 transition-all"
                                        >
                                            <Download className="h-4 w-4" />
                                            Download Answer Key PDF
                                        </Button>
                                    )}
                                </div>

                                <Separator className="opacity-50" />

                                {/* PRIMARY ACTIONS */}
                                <div className="space-y-3">
                                    <span className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/50">Paper Actions</span>
                                    <Button onClick={handlePrint} className="w-full h-12 bg-zinc-900 dark:bg-zinc-100 dark:text-zinc-950 text-white font-bold gap-3 uppercase tracking-widest shadow-xl hover:scale-[1.02] transition-all">
                                        <Printer className="h-4 w-4" />
                                        Print Question Paper
                                    </Button>


                                    {/* Template Rendering Button */}
                                    <div className="mt-2">
                                        <TemplateRenderButton
                                            paperJson={renderPaperJson}
                                            examDate={new Date().toLocaleDateString("en-IN")}
                                            metadataOverride={{
                                                subject: examPaper?.subject || "",
                                                class_name: examPaper?.grade || "",
                                                marks: String(examPaper?.totalMarks || ""),
                                                duration: examPaper?.duration || "",
                                                exam_name: examPaper?.examTitle || "",
                                            }}
                                        />
                                    </div>
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
                                        <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/60 block mb-2">Project Info</span>
                                        <div className="space-y-1.5">
                                            <div className="flex justify-between text-[11px] font-bold uppercase">
                                                <span className="text-muted-foreground">Exam:</span>
                                                <span className="text-foreground truncate ml-4">{currentMetadata?.examTitle || examPaper?.examTitle || "Loading..."}</span>
                                            </div>
                                            <div className="flex justify-between text-[11px] font-bold uppercase">
                                                <span className="text-muted-foreground">Subject:</span>
                                                <span className="text-foreground truncate ml-4">{currentMetadata?.subject || examPaper?.subject || "Loading..."}</span>
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

                        {/* ════ MAIN CONTENT AREA ════ */}
                        <main className="flex-1 overflow-hidden flex flex-col bg-zinc-100/50 dark:bg-zinc-950/50 print:overflow-visible print:h-auto print:bg-white">

                            {/* Tab bar (hidden if answer key not generated yet) */}
                            {answerKeyStatus === "done" && (
                                <div className="flex items-center gap-1 px-6 pt-4 pb-0 print:hidden">
                                    <button
                                        onClick={() => setActiveTab("paper")}
                                        className={cn(
                                            "flex items-center gap-2 px-4 py-2 rounded-t-lg text-xs font-black uppercase tracking-widest border border-b-0 transition-all",
                                            activeTab === "paper"
                                                ? "bg-white dark:bg-zinc-900 border-border/60 text-foreground"
                                                : "bg-transparent border-transparent text-muted-foreground hover:text-foreground"
                                        )}
                                    >
                                        <FileText className="h-3.5 w-3.5" />
                                        Question Paper
                                    </button>
                                    <button
                                        onClick={() => setActiveTab("answerkey")}
                                        className={cn(
                                            "flex items-center gap-2 px-4 py-2 rounded-t-lg text-xs font-black uppercase tracking-widest border border-b-0 transition-all",
                                            activeTab === "answerkey"
                                                ? "bg-white dark:bg-zinc-900 border-border/60 text-foreground"
                                                : "bg-transparent border-transparent text-muted-foreground hover:text-foreground"
                                        )}
                                    >
                                        <KeyRound className="h-3.5 w-3.5" />
                                        Answer Key
                                        <span className="ml-1 h-4 w-4 rounded-full bg-emerald-500 text-white text-[9px] font-black flex items-center justify-center">
                                            ✓
                                        </span>
                                    </button>
                                </div>
                            )}

                            {/* Scrollable content */}
                            <div className="flex-1 overflow-y-auto p-8 md:p-12 print:p-0 custom-scrollbar-thin print:overflow-visible">

                                {/* ── QUESTION PAPER VIEW ── */}
                                <AnimatePresence mode="wait">
                                    {(activeTab === "paper" || answerKeyStatus !== "done") && (
                                        <motion.div
                                            key="paper"
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, y: -10 }}
                                            transition={{ duration: 0.3 }}
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
                                                    {examPaper?.examTitle || "Loading paper..."}
                                                </h1>
                                                <div className="h-1.5 w-24 bg-zinc-900 dark:bg-white mx-auto mb-8 rounded-full print:bg-black" />

                                                <div className="grid grid-cols-2 gap-y-4 text-[13px] font-bold uppercase tracking-widest text-zinc-600 dark:text-zinc-400 print:text-black">
                                                    <div className="text-left border-b border-zinc-100 dark:border-zinc-800 pb-2 inline-block">
                                                        Subject: <span className="text-zinc-950 dark:text-zinc-200 print:text-black outline-none" contentEditable suppressContentEditableWarning>{examPaper?.subject || "Loading..."}</span>
                                                    </div>
                                                    <div className="text-right border-b border-zinc-100 dark:border-zinc-800 pb-2 inline-block">
                                                        Grade/Year: <span className="text-zinc-950 dark:text-zinc-200 print:text-black outline-none" contentEditable suppressContentEditableWarning>{examPaper?.grade || "Loading..."}</span>
                                                    </div>
                                                    <div className="text-left border-b border-zinc-100 dark:border-zinc-800 pb-2 inline-block">
                                                        Duration: <span className="text-zinc-950 dark:text-zinc-200 print:text-black outline-none" contentEditable suppressContentEditableWarning>{examPaper?.duration || "Loading..."}</span>
                                                    </div>
                                                    <div className="text-right border-b border-zinc-100 dark:border-zinc-800 pb-2 inline-block">
                                                        Total Marks: <span className="text-zinc-950 dark:text-zinc-200 print:text-black outline-none" contentEditable suppressContentEditableWarning>{examPaper?.totalMarks ?? "..."}</span>
                                                    </div>
                                                </div>
                                            </header>

                                            <Separator className="mb-12 opacity-30" />

                                            {/* SECTIONS */}
                                            <div className="space-y-12">
                                                {(examPaper?.sections || []).map((section, sIdx) => (
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
                                    )}

                                    {/* ── ANSWER KEY VIEW ── */}
                                    {activeTab === "answerkey" && answerKeyStatus === "done" && answerKeyData && (
                                        <motion.div
                                            key="answerkey"
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, y: -10 }}
                                            transition={{ duration: 0.3 }}
                                            className="mx-auto w-full max-w-[860px] space-y-6"
                                        >
                                            {/* Answer key header */}
                                            <div className="bg-zinc-900 dark:bg-zinc-800 rounded-2xl p-8 text-white text-center">
                                                <div className="flex items-center justify-center gap-3 mb-2">
                                                    <KeyRound className="h-6 w-6 text-rose-400" />
                                                    <h1 className="text-2xl font-black uppercase tracking-tight">Answer Key</h1>
                                                </div>
                                                <p className="text-zinc-400 text-sm">Auto-generated Examination Answer Key · Powered by GPT-4o-mini</p>
                                                <div className="h-0.5 w-16 bg-rose-400 mx-auto mt-4 rounded-full" />
                                            </div>

                                            <AnswerKeyView data={answerKeyData} />

                                            <div className="text-center py-8 text-[10px] uppercase font-black tracking-[0.5em] text-zinc-400">
                                                End of Answer Key · QPilot AI System
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>

                                {/* Loading state (center of main area) */}
                                {answerKeyStatus === "loading" && activeTab === "paper" && (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        className="fixed bottom-8 right-8 flex items-center gap-3 bg-zinc-900 text-white px-5 py-3 rounded-2xl shadow-2xl border border-white/10 z-50"
                                    >
                                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                        <span className="text-xs font-black uppercase tracking-widest">Generating Answer Key…</span>
                                    </motion.div>
                                )}
                            </div>
                        </main>
                    </div>
                </SidebarInset>
            </div>
        </SidebarProvider>
    );
}
