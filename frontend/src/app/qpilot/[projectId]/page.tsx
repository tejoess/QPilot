"use client";

/**
 * app/qpilot/[projectId]/page.tsx
 *
 * Single-page QPilot generation UI.
 * Left column  – input sections (Syllabus, PYQs, Bloom, Pattern, Teacher input)
 * Right column – live log panel + phase indicator
 */

import { useRef, useState, useEffect, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { useUser } from "@clerk/nextjs";
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
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
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
    XCircle,
    Info,
    ChevronRight,
    BookOpen,
    Network,
    BrainCircuit,
    CheckCircle2,
    AlertTriangle,
    Settings2,
    LayoutTemplate,
    Download,
} from "lucide-react";
import { toast } from "sonner";
import { useBloomStore, type BloomKey } from "@/store/bloomStore";
import { usePatternStore, type PatternSection } from "@/store/patternStore";
import { useGenerationFlow, type GenerationConfig } from "@/hooks/useGenerationFlow";
import { useTemplateStore, templatePatternToSections } from "@/store/templateStore";
import { useQPilotConfigStore } from "@/store/qpilotConfigStore";
import { useQPilotStore } from "@/store/qpilotStore";

function Typewriter({ text, delay = 10 }: { text: string; delay?: number }) {
    const [currentText, setCurrentText] = useState("");
    const [currentIndex, setCurrentIndex] = useState(0);

    useEffect(() => {
        if (currentIndex < text.length) {
            const timeout = setTimeout(() => {
                setCurrentText(prevText => prevText + text[currentIndex]);
                setCurrentIndex(prevIndex => prevIndex + 1);
            }, delay);
            return () => clearTimeout(timeout);
        }
    }, [currentIndex, delay, text]);

    return (
        <span>
            {currentText}
            {currentIndex < text.length && <span className="animate-pulse font-black text-primary ml-[2px]">|</span>}
        </span>
    );
}

// ─── Constants ────────────────────────────────────────────────────────────────

const Bubble = ({ icon: Icon, title, content, color, children, isWorking = false }: any) => (
    <div className={`border rounded-xl p-3 w-full animate-in fade-in slide-in-from-bottom-2 duration-500 shadow-sm ${color} relative overflow-hidden group`}>
        {isWorking && (
            <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-current to-transparent opacity-20 skeleton-slide" />
        )}
        <div className="flex items-start gap-2.5">
            <div className={`p-1.5 rounded-full bg-background/50 border shadow-sm ${isWorking ? 'animate-pulse' : ''}`}>
               {isWorking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Icon className="w-3.5 h-3.5" />}
            </div>
            <div className="flex-1 space-y-1">
                <div className="text-[11px] font-bold flex items-center gap-2">
                    {title}
                    {isWorking && (
                        <span className="flex items-center gap-0.5 ml-1">
                            <span className="w-1 h-1 rounded-full bg-current animate-bounce" style={{animationDelay: "0ms"}}/>
                            <span className="w-1 h-1 rounded-full bg-current animate-bounce" style={{animationDelay: "150ms"}}/>
                            <span className="w-1 h-1 rounded-full bg-current animate-bounce" style={{animationDelay: "300ms"}}/>
                        </span>
                    )}
                </div>
                <div className="text-[10px] text-muted-foreground leading-snug">
                    {content}
                </div>
                {children && <div className="pt-1.5">{children}</div>}
            </div>
        </div>
    </div>
);

function RenderAgentTemplate({ file, content }: { file: string; content: any }) {
    if (file === "syllabus.json") {
        const modules = content?.modules || [];
        return (
            <Bubble
                icon={BookOpen}
                title="Syllabus Agent: Extracted Successfully"
                color="bg-primary/5 border-primary/20 text-primary"
                content={<Typewriter text={`I have successfully extracted ${modules.length} modules from your provided syllabus. Wait a moment while I proceed to build the Knowledge Graph.`} />}
            >
                <div className="flex flex-wrap gap-1">
                    {modules.slice(0, 3).map((m: any, idx: number) => (
                        <span key={idx} className="bg-background border border-border/50 px-1.5 py-0.5 rounded text-[9px] truncate max-w-[120px] shadow-sm">
                            {m.module_name || `Module ${m.module_number}`}
                        </span>
                    ))}
                    {modules.length > 3 && <span className="text-[9px] text-muted-foreground px-1 py-0.5">+{modules.length - 3} more</span>}
                </div>
            </Bubble>
        );
    }
    if (file === "knowledge_graph.json") {
        const keys = Object.keys(content || {});
        return (
            <Bubble
                icon={Network}
                title="Data Agent: Knowledge Graph Built"
                color="bg-blue-500/5 border-blue-500/20 text-blue-500"
                content={<Typewriter text={`I just finished drawing the topic relationships into a structured graph! (${keys.length} core concepts mapped).`} />}
            >
                <div className="pl-2 border-l-2 border-blue-500/20 space-y-1">
                    {keys.slice(0, 3).map((k: string, i: number) => (
                        <div key={i} className="text-[9.5px] text-muted-foreground truncate font-medium">{k}</div>
                    ))}
                    {keys.length > 3 && <div className="text-[9px] text-blue-500/50 italic font-mono">...and {keys.length - 3} more sub-trees</div>}
                </div>
            </Bubble>
        );
    }
    if (file === "pyqs_analysis.json") {
        const qCount = content?.total_pyqs || 0;
        if (qCount === 0) {
            return (
                <Bubble
                    icon={AlertTriangle}
                    title="Data Agent: Skipping PYQ Matching"
                    color="bg-amber-500/5 border-amber-500/20 text-amber-600"
                    content={<Typewriter text="No usable questions were found in the provided PYQ data (empty / insufficient length). I will be generating 100% fresh questions directly from the syllabus!" />}
                />
            );
        }
        return (
            <Bubble
                icon={FileText}
                title="Data Agent: Past Questions Analyzed"
                color="bg-rose-500/5 border-rose-500/20 text-rose-600"
                content={<Typewriter text={`I successfully extracted and analyzed ${qCount} unique questions from your past papers. Patterns have been loaded to shape the final blueprint.`} />}
            />
        );
    }
    if (file === "blueprint.json") {
        const sections = content?.sections || [];
        return (
            <Bubble
                icon={FileText}
                title="Blueprint Agent: Drafting Exam Matrix"
                color="bg-emerald-500/5 border-emerald-500/20 text-emerald-600"
                content={<Typewriter text="I am analyzing your course outcomes and constraints. Producing the mathematical distribution matrix! Here is a glimpse:" />}
            >
                <div className="grid grid-cols-2 gap-2 mt-1">
                    {sections.slice(0, 4).map((s: any, idx: number) => (
                        <div key={idx} className="bg-background p-1.5 rounded-md border border-emerald-500/20 text-[9px] text-center shadow-sm">
                            <span className="font-bold text-emerald-600">{s.section_name}</span><br />
                            <span className="text-muted-foreground">{s.questions?.length || 0} Questions</span>
                        </div>
                    ))}
                </div>
            </Bubble>
        );
    }
    if (file === "blueprint_verification.json" || file === "paper_verification.json") {
        const isBlueprint = file.includes("blueprint");
        const verdict = content?.verdict || "UNKNOWN";
        const isOk = verdict === "ACCEPTED" || verdict === "APPROVED";
        
        if (isOk) {
            return (
                <Bubble
                    icon={CheckCircle2}
                    title={`Verifier Agent: ${isBlueprint ? "Blueprint" : "Exam Paper"} Approved!`}
                    color="bg-green-500/5 border-green-500/20 text-green-600"
                    content={<Typewriter text={`I meticulously reviewed the draft and it perfectly matches the parameters and constraints. Validation successful!`} />}
                />
            );
        } else {
            return (
                <Bubble
                    icon={Settings2}
                    title={`Repair Agent: Analyzing and Fixing Draft...`}
                    color="bg-violet-500/5 border-violet-500/20 text-violet-600"
                    isWorking={true}
                    content={<Typewriter text={`I detected some minor imbalances during validation. No problem! I am stepping in to actively reconstruct and repair the draft to perfectly align with your exact constraints right now. Please wait...`} />}
                />
            );
        }
    }
    if (file === "draft_paper.json") {
        return (
            <Bubble
                icon={BrainCircuit}
                title="Generation Agent: Synthesizing Final Questions"
                color="bg-indigo-500/5 border-indigo-500/20 text-indigo-600"
                content={<Typewriter text="I am actively fetching relevant context, cross-referencing your PYQs, and translating Bloom's Taxonomy into varied natural language questions for each section!" />}
            />
        );
    }
    if (file === "final_paper.json") {
        return (
            <Bubble
                icon={CheckCircle2}
                title="SUCCESS: Generation Complete Payload Verified!"
                color="bg-primary/10 border-primary/30 text-primary"
                content={<Typewriter text="Your paper has been officially compiled! Please wait a moment while I prepare the 3D-interactive preview dashboard..." />}
            />
        );
    }
    if (file === "pyqs.json" || file === "blueprint_repair_summary.json" || file === "paper_repair_summary.json" || file === "session_summary.json") {
        return null;
    }
    
    // Default fallback
    const str = JSON.stringify(content, null, 2);
    const truncated = str.length > 500 ? str.slice(0, 500) + "\n... [view truncated]" : str;
    return (
        <pre className="mt-1.5 p-2 rounded-md bg-background border border-border/60 text-[9px] text-muted-foreground overflow-auto max-h-[150px] w-full shadow-sm animate-in fade-in">
            {truncated}
        </pre>
    );
}



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
    { value: "short_notes",  label: "Short Notes" },
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

const STEP_LABELS: Record<string, string> = {
    syllabus_fetch: "Reading syllabus",
    syllabus_format: "Understanding syllabus structure",
    knowledge_graph_build: "Building topic map",
    pyqs_fetch: "Reading previous papers",
    pyqs_format: "Finding PYQ patterns",
    blueprint_build: "Designing paper blueprint",
    blueprint_verify: "Validating blueprint",
    question_select: "Generating questions",
    paper_verify: "Quality-checking paper",
    final_generate: "Finalizing paper",
};

function simplifyLogMessage(message: string): string {
    const m = (message || "").trim();
    if (!m) return "Working on your paper...";
    if (m.includes("rate-limited")) return "High traffic detected. Retrying automatically...";
    if (m.includes("Saved:")) return "Saved intermediate results.";
    if (m.includes("Initial verdict")) return "Running quality checks on the draft.";
    if (m.includes("Final paper verdict")) return "Final quality check completed.";
    if (m.includes("repair loop")) return "Detected imbalance. Auto-correcting the draft.";
    if (m.startsWith("JSON_DATA:")) return "";
    return m.replace(/[^\x20-\x7E]/g, "").trim();
}

function TypingIndicator({ phase }: { phase: string }) {
    const hints: Record<string, string> = {
        syllabus: "Analyzing syllabus and extracting key topics",
        pyqs: "Reviewing previous year papers for patterns",
        generating: "Drafting and validating your final paper",
    };
    const text = hints[phase] || "Processing your request";
    return (
        <div className="rounded-xl border border-border/60 bg-background/60 px-3 py-2">
            <div className="flex items-center gap-2 text-[11px] font-semibold text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                <span>{text}</span>
                <span className="ml-1 flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary/70 animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="h-1.5 w-1.5 rounded-full bg-primary/70 animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="h-1.5 w-1.5 rounded-full bg-primary/70 animate-bounce" style={{ animationDelay: "300ms" }} />
                </span>
            </div>
        </div>
    );
}

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
                <input
                    type="number"
                    disabled={disabled}
                    value={section.optionalQuestions || 0}
                    min={0}
                    max={section.numQuestions}
                    onChange={(e) =>
                        updateSection(section.id, { optionalQuestions: Math.max(0, Math.min(parseInt(e.target.value) || 0, section.numQuestions)) })
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


export default function QPilotBuilderPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const router = useRouter();
    const { user } = useUser();

    // ── Input state ───────────────────────────────────────────────────────────
    const [syllabusMode, setSyllabusMode] = useState<"file" | "text">("file");
    const [syllabusFile, setSyllabusFile] = useState<File | null>(null);
    const [syllabusText, setSyllabusText] = useState("");

    const [pyqsMode, setPyqsMode] = useState<"file" | "text">("file");
    const [pyqsFile, setPyqsFile] = useState<File | null>(null);
    const [pyqsText, setPyqsText] = useState("");
    const [hasPyq, setHasPyq] = useState<boolean>(true);
    const [pyqWeightage, setPyqWeightage] = useState<number>(50);

    const [teacherInput, setTeacherInput] = useState("");

    // ── Stores ────────────────────────────────────────────────────────────────
    const { bloomLevels, setLevel } = useBloomStore();
    const { sections, addSection, getTotalAllocated, getTotalQuestions, getEffectiveAllocated, getEffectiveQuestions, setSections, setTotalMarks } = usePatternStore();

    // ── Template store ────────────────────────────────────────────────────────
    const {
        templates,
        selectedTemplate,
        selectTemplate,
        fetchTemplates,
        isRendering,
        renderPaper,
    } = useTemplateStore();

    const { metadata: projectMeta } = useQPilotConfigStore();
    const { setCurrentMetadata } = useQPilotStore();

    useEffect(() => {
        if (!user) return;
        fetchTemplates();
    }, [fetchTemplates, user?.id]);

    const handleSelectTemplate = (tpl: typeof templates[0]) => {
        if (isRunning) return;
        if (selectedTemplate?.template_id === tpl.template_id) {
            selectTemplate(null);
            return;
        }
        selectTemplate(tpl);
        if (tpl.pattern?.length) {
            setSections(templatePatternToSections(tpl.pattern));
            setTotalMarks(tpl.pattern.reduce((s, p) => s + p.num_parts * p.marks_per_part, 0));
            toast.success(`Pattern autofilled from "${tpl.name}"`);
        }
    };

    const [templateRendering, setTemplateRendering] = useState(false);
    const [templateDone, setTemplateDone] = useState(false);

    const handleRenderTemplate = async () => {
        if (!selectedTemplate || !paperData) return;
        setTemplateRendering(true);
        try {
            await renderPaper(paperData as object, {
                subject: projectMeta.subject || "",
                class_name: projectMeta.grade || "",
                marks: String(getEffectiveAllocated()),
                date: new Date().toLocaleDateString("en-IN"),
                duration: projectMeta.duration || "",
                exam_name: projectMeta.title || "Question Paper",
            });
            setTemplateDone(true);
            toast.success("Downloaded! Check your downloads folder.");
        } catch (e) {
            toast.error("Template render failed. Is backend running?");
        } finally {
            setTemplateRendering(false);
        }
    };

    // ── Generation flow ───────────────────────────────────────────────────────
    const { phase, logs, progressUpdates, error, paperData, runFullGeneration, reset } = useGenerationFlow();
    const isRunning = phase === "syllabus" || phase === "pyqs" || phase === "generating";
    const isDone = phase === "done";
    const combinedTimeline = useMemo(() => {
        // Keep only latest status per step to avoid stale "running" lines after completion
        const latestByStep = new Map<string, (typeof progressUpdates)[number]>();
        for (const p of progressUpdates) latestByStep.set(p.step, p);
        const progressItems = Array.from(latestByStep.values()).map((p, idx) => ({
            key: `p-${idx}-${p.timestamp}`,
            timestamp: p.timestamp,
            kind: "progress" as const,
            message: p.details || `${STEP_LABELS[p.step] || "Working"}...`,
            step: p.step,
            status: p.status,
            progress: p.progress,
        }));

        // De-duplicate repeated log lines
        const dedupedLogs: typeof logs = [];
        for (const l of logs) {
            const prev = dedupedLogs[dedupedLogs.length - 1];
            if (prev && prev.message === l.message && prev.level === l.level) continue;
            dedupedLogs.push(l);
        }
        const logItems = dedupedLogs.map((l, idx) => ({
            key: `l-${idx}-${l.timestamp}`,
            timestamp: l.timestamp,
            kind: "log" as const,
            level: l.level,
            message: l.message,
        }));

        return [...progressItems, ...logItems].sort(
            (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );
    }, [logs, progressUpdates]);

    // Auto-scroll log panel
    const logEndRef = useRef<HTMLDivElement>(null);
    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [logs.length]);

    // Redirect when done — 8s delay so user can click "Generate in Template" first
    useEffect(() => {
        if (isDone) {
            toast.success("Paper generated!", { description: "You can now download it in your template, or view the paper." });
            const t = setTimeout(() => router.push(`/qpilot/${projectId}/resultqp`), 8000);
            return () => clearTimeout(t);
        }
    }, [isDone, projectId, router]);

    // ── Validation ────────────────────────────────────────────────────────────
    const syllabusOk = syllabusMode === "file" ? !!syllabusFile : syllabusText.trim().length > 20;
    const pyqsOk = !hasPyq || (pyqsMode === "file" ? !!pyqsFile : pyqsText.trim().length > 20);
    const bloomTotal = Object.values(bloomLevels).reduce((a, b) => a + b, 0);
    const canGenerate = syllabusOk && pyqsOk && bloomTotal === 100 && !isRunning;

    const handleGenerate = async () => {
        if (!canGenerate) return;
        const effectiveMarks = getEffectiveAllocated() || getTotalAllocated() || 0;
        const effectiveQuestions = getEffectiveQuestions() || getTotalQuestions() || sections.reduce((s, sec) => s + sec.numQuestions, 0);
        setCurrentMetadata({
            examTitle: projectMeta.title || "Question Paper",
            subject: projectMeta.subject || "—",
            grade: projectMeta.grade || "—",
            duration: projectMeta.duration || "3 Hours",
            totalMarks: effectiveMarks,
            totalQuestions: effectiveQuestions,
        });
        const config: GenerationConfig = {
            syllabusFile: syllabusMode === "file" ? (syllabusFile ?? undefined) : undefined,
            syllabusText: syllabusMode === "text" ? syllabusText : undefined,
            pyqsFile: hasPyq && pyqsMode === "file" ? (pyqsFile ?? undefined) : undefined,
            pyqsText: !hasPyq ? `No pyqs available for this subject. Default weightage is ${pyqWeightage}%.` : (pyqsMode === "text" ? `PYQ Weightage: ${pyqWeightage}%.\n\n${pyqsText}` : `PYQ Weightage: ${pyqWeightage}%.`),
            bloomLevels,
            sections,
            totalMarks: getTotalAllocated() || 0,
            totalQuestions: getTotalQuestions() || sections.reduce((s, sec) => s + sec.numQuestions, 0),
            teacherInput: teacherInput.trim() || undefined,
            userId: user?.id || "anonymous",
            projectId: projectId,
            // Metadata from store
            title: projectMeta.title,
            subject: projectMeta.subject,
            grade: projectMeta.grade,
            duration: projectMeta.duration,
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
                                
                                {/* Optional PYQ Toggle */}
                                <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border/40">
                                    <div className="space-y-0.5">
                                        <Label htmlFor="pyq-toggle" className="text-sm font-bold uppercase tracking-wide">Include PYQs?</Label>
                                        <p className="text-[10px] text-muted-foreground font-medium">Toggle if you want to include previous year questions.</p>
                                    </div>
                                    <Switch id="pyq-toggle" checked={hasPyq} onCheckedChange={setHasPyq} disabled={isRunning} />
                                </div>

                                {!hasPyq ? (
                                    <div className="p-4 bg-amber-500/5 border border-amber-500/20 rounded-lg text-amber-600/80">
                                        <p className="text-xs font-bold uppercase tracking-tight flex items-center gap-2">
                                            <AlertTriangle className="h-4 w-4" />
                                            No PYQs Provided
                                        </p>
                                        <p className="text-[10px] mt-1 font-medium">Generation will rely solely on the syllabus context.</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
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
                                    </div>
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
                                                optionalQuestions: 0,
                                                marksPerQuestion: 2,
                                            })
                                        }
                                    >
                                        <Plus className="h-3 w-3 mr-1" />
                                        Add Section
                                    </Button>
                                </div>

                                {/* Template selector */}
                                {templates.length > 0 && (
                                    <div className="space-y-2">
                                        <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                                            Use Template
                                        </p>
                                        <div className="space-y-1.5">
                                            {templates.map((tpl) => {
                                                const isSelected = selectedTemplate?.template_id === tpl.template_id;
                                                const summary = tpl.pattern?.map(
                                                    (p) => `Q${p.question_num}:${p.num_parts}×${p.marks_per_part}M`
                                                ).join(" | ") ?? "";
                                                return (
                                                    <button
                                                        key={tpl.template_id}
                                                        disabled={isRunning}
                                                        onClick={() => handleSelectTemplate(tpl)}
                                                        className={cn(
                                                            "w-full flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-all group",
                                                            isSelected
                                                                ? "border-emerald-500/50 bg-emerald-500/8 shadow-sm"
                                                                : "border-border/50 bg-muted/20 hover:border-primary/30 hover:bg-primary/5",
                                                            isRunning && "opacity-50 cursor-not-allowed"
                                                        )}
                                                    >
                                                        <div className={cn(
                                                            "p-1.5 rounded-md flex-shrink-0",
                                                            isSelected ? "bg-emerald-500/15 text-emerald-600" : "bg-muted text-muted-foreground"
                                                        )}>
                                                            <FileText className="h-3 w-3" />
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <p className="text-[11px] font-bold text-foreground truncate">{tpl.name}</p>
                                                            <p className="text-[10px] text-muted-foreground">{summary}</p>
                                                        </div>
                                                        {isSelected && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 flex-shrink-0" />}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                        {selectedTemplate && (
                                            <p className="text-[10px] text-emerald-600 font-bold flex items-center gap-1">
                                                <CheckCircle2 className="h-3 w-3" />
                                                Pattern autofilled from &quot;{selectedTemplate.name}&quot;
                                            </p>
                                        )}
                                    </div>
                                )}

                                {templates.length === 0 && (
                                    <p className="text-[10px] text-muted-foreground">
                                        <a href="/templates" className="underline text-primary">Upload a template</a> to autofill this section.
                                    </p>
                                )}

                                {sections.length === 0 ? (
                                    <div className="py-8 text-center border-2 border-dashed border-muted rounded-xl text-xs text-muted-foreground">
                                        No sections yet — click <span className="font-bold">Add Section</span> to start.
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        <div className="hidden md:grid grid-cols-[1fr_7rem_3.5rem_4.5rem_3.5rem_2.5rem_1.5rem] gap-2 px-2.5 text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
                                            <span>Name</span><span>Type</span><span>Q&apos;s</span><span>Optional</span><span>Marks</span><span>Total</span><span />
                                        </div>
                                        {sections.map((s) => (
                                            <SectionRow key={s.id} section={s} disabled={isRunning} />
                                        ))}
                                    </div>
                                )}

                                {sections.length > 0 && (
                                    <div className="flex justify-end">
                                        <span className="text-xs font-black text-muted-foreground text-right">
                                            Total: <span className="text-foreground">{getTotalAllocated()} marks, {getTotalQuestions()} questions</span>
                                            <br />
                                            <span className="text-[11px]">After optional: <span className="text-foreground">{getEffectiveAllocated()} marks, {getEffectiveQuestions()} questions</span></span>
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
                        <div className="w-[440px] border-l border-border/50 bg-card/20 flex flex-col overflow-hidden">
                            {/* Panel header */}
                            <div className="px-4 py-3 border-b border-border/40 flex items-center justify-between">
                                <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                                    Live Logs
                                </span>
                                <PhaseBadge phase={phase} />
                            </div>

                            {/* Logs */}
                            <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1.5 font-mono text-[10px]">
                                {combinedTimeline.length === 0 ? (
                                    <p className="text-muted-foreground/50 text-center mt-6">
                                        Starting up agents. Live updates will appear here.
                                    </p>
                                ) : (
                                    combinedTimeline.map((item) => {
                                        if (item.kind === "progress") {
                                            const label = STEP_LABELS[item.step] || "Working";
                                            const done = item.status === "completed";
                                            const failed = item.status === "failed";
                                            return (
                                                <div key={item.key} className="rounded-lg border border-border/50 bg-background/50 px-2.5 py-2">
                                                    <div className="flex items-center justify-between gap-2">
                                                        <span className="text-[10px] font-semibold text-foreground">{label}</span>
                                                        <span className={cn("text-[9px] font-bold uppercase", done ? "text-emerald-600" : failed ? "text-destructive" : "text-primary")}>
                                                            {done ? "done" : failed ? "failed" : "running"}
                                                        </span>
                                                    </div>
                                                    <p className="mt-1 text-[10px] text-muted-foreground">{item.message}</p>
                                                </div>
                                            );
                                        }

                                        const isJson = item.message.startsWith("JSON_DATA:");
                                        if (isJson) {
                                            try {
                                                const payload = JSON.parse(item.message.replace("JSON_DATA:", ""));
                                            const displayContent = <RenderAgentTemplate file={payload.file} content={payload.content} />;
                                            
                                            // Don't render empty shells if RenderAgentTemplate returns null (e.g. for silent JSONs)
                                            if (!displayContent) return null;

                                            return (
                                                    <div key={item.key} className="flex gap-2 items-start mb-1.5 w-full">
                                                    <div className="flex-1 w-full relative">
                                                        {displayContent}
                                                    </div>
                                                </div>
                                            );
                                            } catch {
                                                return null;
                                            }
                                        }
                                        const friendly = simplifyLogMessage(item.message);
                                        if (!friendly) return null;
                                        return (
                                            <div key={item.key} className="rounded-lg border border-border/50 bg-background/60 px-2.5 py-2 text-muted-foreground">
                                                <p className="text-[10px] leading-snug">{friendly}</p>
                                            </div>
                                        );
                                    })
                                )}
                                {isRunning && <TypingIndicator phase={phase} />}
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
                                    <div className="space-y-2">
                                        <Link href={`/qpilot/${projectId}/resultqp`}>
                                            <Button className="w-full h-9 text-xs font-bold gap-2">
                                                <CheckCircle2 className="h-3.5 w-3.5" />
                                                View Paper
                                                <ChevronRight className="h-3.5 w-3.5" />
                                            </Button>
                                        </Link>

                                        {/* Generate in Template */}
                                        {selectedTemplate && paperData && (
                                            <button
                                                disabled={templateRendering || templateDone}
                                                onClick={handleRenderTemplate}
                                                className={cn(
                                                    "w-full flex items-center gap-2.5 p-3 rounded-xl border text-left transition-all",
                                                    templateDone
                                                        ? "border-emerald-500/40 bg-emerald-500/8"
                                                        : "border-primary/30 bg-primary/5 hover:bg-primary/10",
                                                    (templateRendering || templateDone) && "cursor-not-allowed opacity-80"
                                                )}
                                            >
                                                <div className={cn(
                                                    "p-1.5 rounded-lg flex-shrink-0",
                                                    templateDone ? "bg-emerald-500/15 text-emerald-600" : "bg-primary/10 text-primary"
                                                )}>
                                                    <LayoutTemplate className="h-4 w-4" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-[11px] font-bold text-foreground">
                                                        {templateDone ? "Downloaded!" : "Generate in Template"}
                                                    </p>
                                                    <p className="text-[10px] text-muted-foreground truncate">
                                                        {templateDone
                                                            ? `Rendered into "${selectedTemplate.name}"`
                                                            : `Fill into "${selectedTemplate.name}"`
                                                        }
                                                    </p>
                                                </div>
                                                <div className="flex-shrink-0">
                                                    {templateRendering ? (
                                                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                                    ) : templateDone ? (
                                                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                                                    ) : (
                                                        <Download className="h-4 w-4 text-primary" />
                                                    )}
                                                </div>
                                            </button>
                                        )}
                                    </div>
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
