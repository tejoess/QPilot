"use client";

/**
 * app/templates/page.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * "Your Templates" page — users can upload DOCX exam templates.
 * The app extracts placeholders and pattern and stores them for autofill
 * during paper generation.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useEffect, useRef, useState } from "react";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { QPilotSidebar } from "@/components/qpilot/QPilotSidebar";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useTemplateStore, TemplatePattern } from "@/store/templateStore";
import {
    Upload,
    FileText,
    Trash2,
    CheckCircle2,
    LayoutTemplate,
    Loader2,
    ChevronRight,
    Info,
    Download,
    Eye,
    Trash
} from "lucide-react";
import { cn } from "@/lib/utils";

function PatternBadge({ pattern }: { pattern: TemplatePattern[] }) {
    if (!pattern || pattern.length === 0) return null;
    const summary = pattern.map(p => `Q${p.question_num}: ${p.num_parts}×${p.marks_per_part}M`).join(" | ");
    return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-400">
            {summary}
        </span>
    );
}

export default function TemplatesPage() {
    const { templates, isUploading, fetchTemplates, uploadTemplate, deleteTemplate } = useTemplateStore();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [dragOver, setDragOver] = useState(false);

    useEffect(() => {
        fetchTemplates();
    }, [fetchTemplates]);

    const handleFileSelected = async (file: File) => {
        if (!file.name.endsWith(".docx")) {
            toast.error("Only .docx files are supported.");
            return;
        }
        const toastId = toast.loading(`Uploading "${file.name}"...`);
        const result = await uploadTemplate(file);
        if (result) {
            toast.success(`Template uploaded!`, {
                id: toastId,
                description: `Pattern extracted: ${result.pattern.length} question group(s).`,
            });
        } else {
            toast.error("Upload failed. Is the backend running?", { id: toastId });
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFileSelected(file);
    };

    return (
        <SidebarProvider style={{
            "--sidebar-width": "240px",
            "--sidebar-width-icon": "70px"
        } as React.CSSProperties}>
            <div className="flex h-screen w-full bg-background overflow-hidden">
                <QPilotSidebar />
                <SidebarInset className="flex-1 overflow-auto bg-slate-50/30 dark:bg-slate-950/20">
                    <main className="max-w-4xl mx-auto px-6 py-10 space-y-10">

                        {/* Header */}
                        <div className="space-y-3">
                            <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-[0.2em]">
                                <LayoutTemplate className="h-3 w-3" />
                                QPilot Templates
                            </div>
                            <h1 className="text-3xl font-bold tracking-tight text-foreground">Your Templates</h1>
                            <p className="text-sm text-muted-foreground max-w-xl">
                                Upload your institution&#39;s DOCX exam template. QPilot will extract the question pattern and placeholders,
                                so you can auto-fill the paper pattern during generation and download the final paper in your template format.
                            </p>
                        </div>

                        {/* Info Banner */}
                        <div className="flex items-start gap-3 bg-blue-500/5 border border-blue-500/20 rounded-xl p-4 text-sm text-blue-700 dark:text-blue-300">
                            <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                            <div>
                                <p className="font-bold mb-1">Template Requirements</p>
                                <p className="text-xs opacity-80">
                                    Your DOCX must contain bracket-style placeholders: <code className="bg-blue-500/10 px-1 rounded">[subject]</code>,{" "}
                                    <code className="bg-blue-500/10 px-1 rounded">[class]</code>,{" "}
                                    <code className="bg-blue-500/10 px-1 rounded">[marks]</code>,{" "}
                                    <code className="bg-blue-500/10 px-1 rounded">[date]</code>,{" "}
                                    <code className="bg-blue-500/10 px-1 rounded">[duration]</code>,{" "}
                                    <code className="bg-blue-500/10 px-1 rounded">[exam_name]</code>,{" "}
                                    and question slots like <code className="bg-blue-500/10 px-1 rounded">[1a]</code>,{" "}
                                    <code className="bg-blue-500/10 px-1 rounded">[2a]</code> etc.
                                    The <code className="bg-blue-500/10 px-1 rounded">[cl]</code> placeholder in the same row as a question will be mapped to the cognitive level.
                                </p>
                            </div>
                        </div>

                        {/* Upload Button */}
                        <div className="flex justify-end pt-4">
                            <Button 
                                onClick={() => fileInputRef.current?.click()}
                                className="bg-primary text-primary-foreground font-bold shadow-lg shadow-primary/20 hover:scale-105 transition-all w-full md:w-auto"
                                disabled={isUploading}
                                size="lg"
                            >
                                {isUploading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
                                Upload New Template
                            </Button>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".docx"
                                className="hidden"
                                onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    if (file) handleFileSelected(file);
                                    e.target.value = "";
                                }}
                            />
                        </div>

                        {/* Templates List */}
                        {templates.length > 0 && (
                            <div className="space-y-4 pb-20">
                                <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground">Uploaded Templates</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {templates.map((tpl) => (
                                        <div
                                            key={tpl.template_id}
                                            className="flex flex-col p-6 bg-card border border-border/50 rounded-xl shadow-sm hover:shadow-md transition-all gap-4"
                                        >
                                            <div className="flex justify-between items-start">
                                                <div className="p-3 rounded-lg bg-primary/10 text-primary w-fit">
                                                    <FileText className="h-6 w-6" />
                                                </div>
                                                <div className="flex items-center gap-1 text-[10px] text-emerald-600 font-bold bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                                                    <CheckCircle2 className="h-3 w-3" /> Ready
                                                </div>
                                            </div>

                                            <div className="flex-1 min-w-0">
                                                <p className="font-bold text-lg text-foreground truncate">{tpl.name}</p>
                                                <div className="mt-2">
                                                    <PatternBadge pattern={tpl.pattern} />
                                                </div>
                                            </div>

                                            <div className="flex gap-2 mt-2">
                                                <Button variant="outline" size="sm" className="flex-1 text-xs shadow-none px-2"><Eye className="h-3 w-3 mr-1"/> Open</Button>
                                                <Button variant="outline" size="sm" className="flex-1 text-xs shadow-none px-2"><Download className="h-3 w-3 mr-1"/> Link</Button>
                                            </div>
                                            <Button variant="ghost" size="sm" className="w-full text-xs text-destructive hover:bg-destructive/10 mt-1" onClick={() => deleteTemplate(tpl.template_id)}><Trash className="h-3 w-3 mr-1"/> Delete (Azure)</Button>
                                        </div>
                                    ))}
                                </div>
                                <p className="text-xs text-muted-foreground italic">
                                    These templates will appear in the Paper Pattern step during generation.
                                </p>
                            </div>
                        )}

                        {templates.length === 0 && !isUploading && (
                            <div className="text-center py-8 text-muted-foreground text-sm font-medium">
                                No templates yet. Upload your first DOCX template above.
                            </div>
                        )}
                    </main>
                </SidebarInset>
            </div>
        </SidebarProvider>
    );
}
