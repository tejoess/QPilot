"use client";

/**
 * components/qpilot/TemplateRenderButton.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Shown on the generation complete screen when a template is selected.
 * Calls backend /templates/render and triggers a DOCX download.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useTemplateStore } from "@/store/templateStore";
import { useQPilotConfigStore } from "@/store/qpilotConfigStore";
import { useUser } from "@clerk/nextjs";
import {
    Download,
    Loader2,
    FileText,
    LayoutTemplate,
    CheckCircle2,
    XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface TemplateRenderButtonProps {
    /** The generated paper JSON object */
    paperJson: object | null;
    /** Optional override for date string */
    examDate?: string;
    className?: string;
}

export function TemplateRenderButton({ paperJson, examDate, className }: TemplateRenderButtonProps) {
    const { user } = useUser();
    const { projectId } = useParams();
    const { selectedTemplate, isRendering, renderPaper, setUserId } = useTemplateStore();
    const { metadata } = useQPilotConfigStore();
    const [done, setDone] = useState(false);

    if (!selectedTemplate) return null;
    if (!paperJson) return null;

    const handleRender = async () => {
        // Ensure user ID is synced with store
        if (user?.id) setUserId(user.id);

        const toastId = toast.loading(`Rendering into "${selectedTemplate.name}"...`);
        try {
            await renderPaper(paperJson, {
                subject: metadata.subject || "",
                class_name: metadata.grade || "",
                marks: String(metadata.totalMarks || ""),
                date: examDate || new Date().toLocaleDateString("en-IN"),
                duration: metadata.duration || "",
                exam_name: metadata.title || "",
                project_id: projectId as string,
            });
            toast.success("Downloaded! Check your downloads folder.", { id: toastId });
            setDone(true);
        } catch (err) {
            const e = err as { message?: string };
            toast.error("Render failed", {
                id: toastId,
                description: e?.message || "Ensure backend is running.",
            });
        }
    };

    return (
        <div className={cn(
            "flex items-center gap-3 p-4 rounded-2xl border bg-card shadow-sm",
            done ? "border-emerald-500/30 bg-emerald-500/5" : "border-primary/20 bg-primary/3",
            className
        )}>
            <div className={cn(
                "p-2.5 rounded-xl flex-shrink-0",
                done ? "bg-emerald-500/15 text-emerald-600" : "bg-primary/10 text-primary"
            )}>
                <LayoutTemplate className="h-5 w-5" />
            </div>

            <div className="flex-1 min-w-0 pr-2">
                <p className="text-sm font-bold text-foreground truncate whitespace-normal leading-tight">
                    {done ? "Template Generated!" : "Generate in Template"}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                    {done
                        ? `Downloaded as "${selectedTemplate.name.replace(".docx", "_filled.docx")}"`
                        : `Fill into "${selectedTemplate.name}" · Pattern: ${selectedTemplate.pattern?.length ?? 0} section(s)`
                    }
                </p>
            </div>

            <Button
                size="sm"
                onClick={handleRender}
                disabled={isRendering || done}
                className={cn(
                    "flex-shrink-0 gap-2 font-bold text-xs",
                    done
                        ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                        : "bg-primary shadow-lg shadow-primary/20"
                )}
            >
                {isRendering ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : done ? (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                ) : (
                    <Download className="h-3.5 w-3.5" />
                )}
                <span className="hidden sm:inline">{isRendering ? "Rendering…" : done ? "Downloaded" : "Get DOCX"}</span>
                <span className="sm:hidden">{done ? "Done" : "DOCX"}</span>
            </Button>
        </div>
    );
}
