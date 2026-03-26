"use client";

/**
 * app/qpilot/[projectId]/page.tsx
 *
 * Single-page QPilot generation UI.
 * Left column  – input sections (Syllabus, PYQs, Bloom, Pattern, Teacher input)
 * Right column – live log panel + phase indicator
 */

import { useRef, useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { QPilotSidebar } from "@/components/qpilot/QPilotSidebar";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import {
    Upload,
    FileText,
    Trash2,
    Plus,
    Hash,
    Award,
    Zap,
    Loader2,
    CheckCircle2,
    XCircle,
    Info,
    ChevronRight,
    AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { useBloomStore, type BloomKey } from "@/store/bloomStore";
import { usePatternStore, type PatternSection } from "@/store/patternStore";
import { useGenerationFlow, type GenerationConfig } from "@/hooks/useGenerationFlow";

// ─── Constants ────────────────────────────────────────────────────────────────

const BLOOM_LABELS: { key: BloomKey; label: string; color: string }[] = [
    { key: "remember",   label: "Remember",   color: "bg-rose-400" },
    { key: "understand", label: "Understand",  color: "bg-orange-400" },
    { key: "apply",      label: "Apply",       color: "bg-amber-400" },
    { key: "analyze",    label: "Analyze",     color: "bg-emerald-400" },
    { key: "evaluate",   label: "Evaluate",    color: "bg-sky-400" },
    { key: "create",     label: "Create",      color: "bg-violet-400" },
];

const QUESTION_TYPES = [
    { value: "mcq",          label: "MCQ" },
    { value: "short_answer", label: "Short Answer" },
    { value: "long_answer",  label: "Long Answer" },
    { value: "case_study",   label: "Case Study" },
];

const PHASE_LABELS: Record<string, string> = {
    idle:       "Ready",
    syllabus:   "Analysing Syllabus…",
    pyqs:       "Analysing PYQs…",
    generating: "Generating Paper…",
    done:       "Done",
    error:      "Error",
};

// ─── File input helper ────────────────────────────────────────────────────────

function FileUploadArea({
    file,
    onFile,
    disabled,
}: {
    file: File | null;
    onFile: (f: File | null) => void;
    disabled?: boolean;
}) {
    const ref = useRef<HTMLInputElement>(null);

    return (
        <div
            onClick={() => !disabled && ref.current?.click()}
            className={cn(
                "border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-colors",
                disabled ? "opacity-50 cursor-not-allowed" : "hover:border-primary/60 hover:bg-primary/5",
                file ? "border-emerald-500/60 bg-emerald-500/5" : "border-border/50"
            )}
        >
            <input
                ref={ref}
                type="file"
                accept=".pdf"
                className="hidden"
                disabled={disabled}
                onChange={(e) => onFile(e.target.files?.[0] ?? null)}
            />
            {file ? (
                <div className="flex items-center justify-center gap-2 text-emerald-600">
                    <FileText className="h-4 w-4" />
                    <span className="text-xs font-bold truncate max-w-[200px]">{file.name}</span>
                    <button
                        onClick={(e) => { e.stopPropagation(); onFile(null); }}
                        className="ml-1 text-muted-foreground hover:text-destructive"
                    >
                        <Trash2 className="h-3.5 w-3.5" />
                    </button>
                </div>
            ) : (
                <div className="flex flex-col items-center gap-1.5 text-muted-foreground">
                    <Upload className="h-5 w-5" />
                    <span className="text-xs font-semibold">Click to upload PDF</span>
                </div>
            )}
        </div>
    );
}

// ─── Section row for pattern builder ─────────────────────────────────────────

function SectionRow({
    section,
    disabled,
}: {
    section: PatternSection;
    disabled?: boolean;
}) {
    const { updateSection, deleteSection } = usePatternStore();
    return (
        <div className="flex items-center gap-2 p-2.5 bg-muted/30 rounded-lg border border-border/40 group">
            <Input
                value={section.name}
                disabled={disabled}
                onChange={(e) => updateSection(section.id, { name: e.target.value })}
                className="h-7 text-xs font-bold flex-1 min-w-0"
            />
            <Select
                value={section.type}
                disabled={disabled}
                onValueChange={(v) => updateSection(section.id, { type: v })}
            >
                <SelectTrigger className="h-7 w-28 text-xs">
                    <SelectValue />
                </SelectTrigger>
                <SelectContent>
                    {QUESTION_TYPES.map((t) => (
                        <SelectItem key={t.value} value={t.value} className="text-xs">
                            {t.label}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
            <div className="flex items-center h-7 bg-background rounded border border-border/60 px-1.5 w-14">
                <Hash className="h-2.5 w-2.5 text-muted-foreground mr-1 shrink-0" />
                <input
                    type="number"
                    disabled={disabled}
                    value={section.numQuestions}
                    min={1}
                    onChange={(e) =>
                        updateSection(section.id, { numQuestions: parseInt(e.target.value) || 1 })
                    }
                    className="w-full text-xs font-bold bg-transparent outline-none"
                />
            </div>
            <div className="flex items-center h-7 bg-background rounded border border-border/60 px-1.5 w-14">
                <Award className="h-2.5 w-2.5 text-muted-foreground mr-1 shrink-0" />
                <input
                    type="number"
                    disabled={disabled}
                    value={section.marksPerQuestion}
                    min={1}
                    onChange={(e) =>
                        updateSection(section.id, { marksPerQuestion: parseInt(e.target.value) || 1 })
                    }
                    className="w-full text-xs font-bold bg-transparent outline-none"
                />
            </div>
            <span className="text-[10px] font-black text-emerald-600 w-10 text-right shrink-0">
                {section.totalMarks}M
            </span>
            <button
                disabled={disabled}
                onClick={() => deleteSection(section.id)}
                className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive disabled:cursor-not-allowed"
            >
                <Trash2 className="h-3.5 w-3.5" />
            </button>
        </div>
    );
}

// ─── Small helper components ──────────────────────────────────────────────────

function SectionLabel({ index, title }: { index: number; title: string }) {
    return (
        <div className="flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-primary text-primary-foreground text-[10px] font-black flex items-center justify-center shrink-0">
                {index}
            </span>
            <h2 className="text-sm font-black uppercase tracking-tight text-foreground">{title}</h2>
        </div>
    );
}

function ModeToggle({
    mode,
    onMode,
    disabled,
}: {
    mode: "file" | "text";
    onMode: (m: "file" | "text") => void;
    disabled?: boolean;
}) {
    return (
        <div className="flex gap-1 p-1 bg-muted rounded-lg w-fit">
            {(["file", "text"] as const).map((m) => (
                <button
                    key={m}
                    disabled={disabled}
                    onClick={() => onMode(m)}
                    className={cn(
                        "px-3 py-1 rounded-md text-xs font-bold transition-colors uppercase tracking-wide",
                        mode === m
                            ? "bg-background text-foreground shadow-sm"
                            : "text-muted-foreground hover:text-foreground"
                    )}
                >
                    {m === "file" ? "Upload PDF" : "Paste Text"}
                </button>
            ))}
        </div>
    );
}

function PhaseBadge({ phase }: { phase: string }) {
    const colors: Record<string, string> = {
        idle:       "bg-muted text-muted-foreground",
        syllabus:   "bg-blue-100 text-blue-700 border-blue-200",
        pyqs:       "bg-indigo-100 text-indigo-700 border-indigo-200",
        generating: "bg-amber-100 text-amber-700 border-amber-200",
        done:       "bg-emerald-100 text-emerald-700 border-emerald-200",
        error:      "bg-destructive/10 text-destructive border-destructive/20",
    };
    return (
        <Badge className={cn("text-[9px] font-black uppercase tracking-wider border px-2 py-0.5 flex items-center gap-1", colors[phase] || colors.idle)}>
            {(phase === "syllabus" || phase === "pyqs" || phase === "generating") && (
                <Loader2 className="h-2.5 w-2.5 animate-spin" />
            )}
            {phase === "done" && <CheckCircle2 className="h-2.5 w-2.5" />}
            {phase === "error" && <XCircle className="h-2.5 w-2.5" />}
            {PHASE_LABELS[phase] ?? phase}
        </Badge>
    );
}

function LogIcon({ level }: { level: "info" | "warning" | "error" }) {
    if (level === "error") return <XCircle className="h-2.5 w-2.5 text-destructive shrink-0 mt-0.5" />;
    if (level === "warning") return <AlertTriangle className="h-2.5 w-2.5 text-amber-500 shrink-0 mt-0.5" />;
    return <Info className="h-2.5 w-2.5 text-primary/50 shrink-0 mt-0.5" />;
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function QPilotPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const router = useRouter();

    // ── Input state ───────────────────────────────────────────────────────────
    const [syllabusMode, setSyllabusMode] = useState<"file" | "text">("file");
    const [syllabusFile, setSyllabusFile] = useState<File | null>(null);
    const [syllabusText, setSyllabusText] = useState("");

    const [pyqsMode, setPyqsMode] = useState<"file" | "text">("file");
    const [pyqsFile, setPyqsFile] = useState<File | null>(null);
    const [pyqsText, setPyqsText] = useState("");

    const [teacherInput, setTeacherInput] = useState("");

    // ── Stores ────────────────────────────────────────────────────────────────
    const { bloomLevels, setLevel } = useBloomStore();
    const { sections, addSection, getTotalAllocated, getTotalQuestions } = usePatternStore();

    // ── Generation flow ───────────────────────────────────────────────────────
    const { phase, logs, error, runFullGeneration, reset } = useGenerationFlow();
    const isRunning = phase === "syllabus" || phase === "pyqs" || phase === "generating";
    const isDone = phase === "done";

    // Auto-scroll log panel
    const logEndRef = useRef<HTMLDivElement>(null);
    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logs.length]);

    // Redirect when done
    useEffect(() => {
        if (isDone) {
            toast.success("Paper generated!", { description: "Redirecting to result…" });
            const t = setTimeout(() => router.push(`/qpilot/${projectId}/resultqp`), 2000);
            return () => clearTimeout(t);
        }
    }, [isDone, projectId, router]);

    // ── Validation ────────────────────────────────────────────────────────────
    const syllabusOk = syllabusMode === "file" ? !!syllabusFile : syllabusText.trim().length > 20;
    const pyqsOk = pyqsMode === "file" ? !!pyqsFile : pyqsText.trim().length > 20;
    const bloomTotal = Object.values(bloomLevels).reduce((a, b) => a + b, 0);
    const canGenerate = syllabusOk && pyqsOk && bloomTotal === 100 && !isRunning;

    const handleGenerate = async () => {
        if (!canGenerate) return;
        const config: GenerationConfig = {
            syllabusFile: syllabusMode === "file" ? (syllabusFile ?? undefined) : undefined,
            syllabusText: syllabusMode === "text" ? syllabusText : undefined,
            pyqsFile: pyqsMode === "file" ? (pyqsFile ?? undefined) : undefined,
            pyqsText: pyqsMode === "text" ? pyqsText : undefined,
            bloomLevels,
            sections,
            totalMarks: getTotalAllocated() || 0,
            totalQuestions: getTotalQuestions() || sections.reduce((s, sec) => s + sec.numQuestions, 0),
            teacherInput: teacherInput.trim() || undefined,
        };
        await runFullGeneration(config);
    };

    return (
        <SidebarProvider
            style={{ "--sidebar-width": "240px", "--sidebar-width-icon": "70px" } as React.CSSProperties}
        >
            <div className="flex h-screen w-full overflow-hidden bg-background">
                <QPilotSidebar />

                <SidebarInset className="flex-1 overflow-hidden">
                    {/* ── Two-column body ── */}
                    <div className="flex h-full overflow-hidden">

                        {/* ════ LEFT: Input sections ════ */}
                        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-7">

                            {/* Header */}
                            <div>
                                <h1 className="text-xl font-black uppercase tracking-tight text-foreground flex items-center gap-2">
                                    <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-black italic text-sm">Q</div>
                                    Generate Question Paper
                                </h1>
                                <p className="text-xs text-muted-foreground mt-1 font-medium">
                                    Fill in all sections, then click <span className="font-bold text-foreground">Generate</span>.
                                </p>
                            </div>

                            {/* ── 1. Syllabus ── */}
                            <section className="space-y-3">
                                <SectionLabel index={1} title="Syllabus" />
                                <ModeToggle mode={syllabusMode} onMode={setSyllabusMode} disabled={isRunning} />
                                {syllabusMode === "file" ? (
                                    <FileUploadArea file={syllabusFile} onFile={setSyllabusFile} disabled={isRunning} />
                                ) : (
                                    <Textarea
                                        placeholder="Paste syllabus text here…"
                                        value={syllabusText}
                                        disabled={isRunning}
                                        onChange={(e) => setSyllabusText(e.target.value)}
                                        className="h-[120px] text-xs resize-none overflow-y-auto"
                                    />
                                )}
                            </section>

                            <Separator />

                            {/* ── 2. Previous Year Questions ── */}
                            <section className="space-y-3">
                                <SectionLabel index={2} title="Previous Year Questions (PYQs)" />
                                <ModeToggle mode={pyqsMode} onMode={setPyqsMode} disabled={isRunning} />
                                {pyqsMode === "file" ? (
                                    <FileUploadArea file={pyqsFile} onFile={setPyqsFile} disabled={isRunning} />
                                ) : (
                                    <Textarea
                                        placeholder="Paste previous year questions here…"
                                        value={pyqsText}
                                        disabled={isRunning}
                                        onChange={(e) => setPyqsText(e.target.value)}
                                        className="h-[120px] text-xs resize-none overflow-y-auto"
                                    />
                                )}
                            </section>

                            <Separator />

                            {/* ── 3. Bloom's Taxonomy ── */}
                            <section className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <SectionLabel index={3} title="Bloom's Taxonomy Distribution" />
                                    <span
                                        className={cn(
                                            "text-xs font-black px-2 py-0.5 rounded border",
                                            bloomTotal === 100
                                                ? "text-emerald-600 bg-emerald-50 border-emerald-200"
                                                : "text-amber-600 bg-amber-50 border-amber-200"
                                        )}
                                    >
                                        {bloomTotal} / 100%
                                    </span>
                                </div>
                                <div className="space-y-3">
                                    {BLOOM_LABELS.map(({ key, label, color }) => (
                                        <div key={key} className="space-y-1">
                                            <div className="flex items-center justify-between text-xs">
                                                <span className="font-semibold text-muted-foreground">{label}</span>
                                                <span className="font-black tabular-nums">{bloomLevels[key]}%</span>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <input
                                                    type="range"
                                                    min={0}
                                                    max={100}
                                                    step={5}
                                                    value={bloomLevels[key]}
                                                    disabled={isRunning}
                                                    onChange={(e) => setLevel(key, parseInt(e.target.value))}
                                                    className="flex-1 accent-primary h-1.5 cursor-pointer disabled:cursor-not-allowed"
                                                />
                                                <div
                                                    className={cn("h-2 rounded-full transition-all", color)}
                                                    style={{ width: `${bloomLevels[key]}%`, minWidth: "4px", maxWidth: "72px" }}
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                {bloomTotal !== 100 && (
                                    <p className="text-xs text-amber-600 flex items-center gap-1.5 font-semibold">
                                        <AlertTriangle className="h-3.5 w-3.5" />
                                        Levels must sum to 100% before generating.
                                    </p>
                                )}
                            </section>

                            <Separator />

                            {/* ── 4. Paper Pattern ── */}
                            <section className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <SectionLabel index={4} title="Paper Pattern" />
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        disabled={isRunning}
                                        className="h-7 px-3 text-xs font-bold"
                                        onClick={() =>
                                            addSection({
                                                name: `Section ${String.fromCharCode(65 + sections.length)}`,
                                                type: "short_answer",
                                                numQuestions: 5,
                                                marksPerQuestion: 2,
                                            })
                                        }
                                    >
                                        <Plus className="h-3 w-3 mr-1" />
                                        Add Section
                                    </Button>
                                </div>

                                {sections.length === 0 ? (
                                    <div className="py-8 text-center border-2 border-dashed border-muted rounded-xl text-xs text-muted-foreground">
                                        No sections yet — click <span className="font-bold">Add Section</span> to start.
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        <div className="hidden md:grid grid-cols-[1fr_7rem_3.5rem_3.5rem_2.5rem_1.5rem] gap-2 px-2.5 text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                                            <span>Name</span><span>Type</span><span>Q&apos;s</span><span>Marks</span><span>Total</span><span />
                                        </div>
                                        {sections.map((s) => (
                                            <SectionRow key={s.id} section={s} disabled={isRunning} />
                                        ))}
                                    </div>
                                )}

                                {sections.length > 0 && (
                                    <div className="flex justify-end">
                                        <span className="text-xs font-black text-muted-foreground">
                                            Total: <span className="text-foreground">{getTotalAllocated()} marks, {getTotalQuestions()} questions</span>
                                        </span>
                                    </div>
                                )}
                            </section>

                            <Separator />

                            {/* ── 5. Teacher Instructions ── */}
                            <section className="space-y-3">
                                <SectionLabel index={5} title="Teacher Instructions (Optional)" />
                                <Textarea
                                    placeholder="e.g. Focus more on calculus, avoid repetition from PYQs, add at least 2 HOTS questions…"
                                    value={teacherInput}
                                    disabled={isRunning}
                                    onChange={(e) => setTeacherInput(e.target.value)}
                                    className="min-h-[90px] text-xs resize-y"
                                />
                            </section>

                            {/* ── Generate Button ── */}
                            <div className="pb-8">
                                <Button
                                    size="lg"
                                    disabled={!canGenerate}
                                    onClick={handleGenerate}
                                    className="w-full h-12 text-sm font-black uppercase tracking-widest gap-2"
                                >
                                    {isRunning ? (
                                        <>
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                            {PHASE_LABELS[phase]}
                                        </>
                                    ) : (
                                        <>
                                            <Zap className="h-4 w-4" />
                                            Generate Question Paper
                                        </>
                                    )}
                                </Button>
                                {!syllabusOk && (
                                    <p className="text-xs text-muted-foreground mt-2 text-center">Upload or paste syllabus to continue.</p>
                                )}
                                {syllabusOk && !pyqsOk && (
                                    <p className="text-xs text-muted-foreground mt-2 text-center">Upload or paste PYQs to continue.</p>
                                )}
                            </div>
                        </div>

                        {/* ════ RIGHT: Log panel ════ */}
                        <div className="w-[340px] border-l border-border/50 bg-card/20 flex flex-col overflow-hidden">
                            {/* Panel header */}
                            <div className="px-4 py-3 border-b border-border/40 flex items-center justify-between">
                                <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                                    Live Logs
                                </span>
                                <PhaseBadge phase={phase} />
                            </div>

                            {/* Logs */}
                            <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1.5 font-mono text-[10px]">
                                {logs.length === 0 ? (
                                    <p className="text-muted-foreground/50 text-center mt-6">
                                        Logs will appear here once generation starts.
                                    </p>
                                ) : (
                                    logs.map((log, i) => (
                                        <div key={i} className="flex gap-1.5 items-start">
                                            <LogIcon level={log.level} />
                                            <span
                                                className={cn(
                                                    "leading-relaxed",
                                                    log.level === "error" && "text-destructive",
                                                    log.level === "warning" && "text-amber-600",
                                                    log.level === "info" && "text-foreground/80"
                                                )}
                                            >
                                                {log.message}
                                            </span>
                                        </div>
                                    ))
                                )}
                                <div ref={logEndRef} />
                            </div>

                            {/* Footer actions */}
                            <div className="p-3 border-t border-border/40 space-y-2">
                                {phase === "error" && (
                                    <div className="p-2 bg-destructive/10 rounded text-xs text-destructive font-semibold border border-destructive/20">
                                        {error || "Generation failed. Check logs above."}
                                    </div>
                                )}
                                {isDone && (
                                    <Link href={`/qpilot/${projectId}/resultqp`}>
                                        <Button className="w-full h-9 text-xs font-bold gap-2">
                                            <CheckCircle2 className="h-3.5 w-3.5" />
                                            View Paper
                                            <ChevronRight className="h-3.5 w-3.5" />
                                        </Button>
                                    </Link>
                                )}
                                {(phase === "done" || phase === "error") && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="w-full h-8 text-xs"
                                        onClick={reset}
                                    >
                                        Reset
                                    </Button>
                                )}
                            </div>
                        </div>
                    </div>
                </SidebarInset>
            </div>
        </SidebarProvider>
    );
}
