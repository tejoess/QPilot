"use client";

/**
 * components/qpilot/TemplateSelector.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Shows uploaded templates in the PaperPatternAgentCard so user can select one
 * and auto-fill the pattern sections.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useEffect } from "react";
import { useTemplateStore, templatePatternToSections } from "@/store/templateStore";
import { usePatternStore } from "@/store/patternStore";
import { Button } from "@/components/ui/button";
import {
    LayoutTemplate,
    CheckCircle2,
    ChevronRight,
    ExternalLink,
    FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { useUser } from "@clerk/nextjs";

interface TemplateSelectorProps {
    disabled?: boolean;
}

export function TemplateSelector({ disabled }: TemplateSelectorProps) {
    const { templates, selectedTemplate, selectTemplate, fetchTemplates, userId } = useTemplateStore();
    const { isLoaded, user } = useUser();
    const { setSections, setTotalMarks } = usePatternStore();

    useEffect(() => {
        if (!isLoaded || !user) return;
        fetchTemplates();
    }, [fetchTemplates, isLoaded, user?.id, userId]);

    if (templates.length === 0) {
        return (
            <div className="flex items-center justify-between py-2 px-3 rounded-lg bg-muted/20 border border-dashed border-border/60">
                <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                    <LayoutTemplate className="h-3.5 w-3.5" />
                    No templates uploaded yet
                </div>
                <Link href="/templates" target="_blank">
                    <Button variant="ghost" size="sm" className="h-6 text-[10px] font-bold gap-1 text-primary hover:bg-primary/10">
                        Upload <ExternalLink className="h-2.5 w-2.5" />
                    </Button>
                </Link>
            </div>
        );
    }

    const handleSelectTemplate = (tpl: typeof templates[0]) => {
        if (disabled) return;

        // Toggle off if clicking the same one
        if (selectedTemplate?.template_id === tpl.template_id) {
            selectTemplate(null);
            return;
        }

        selectTemplate(tpl);

        // Autofill the pattern sections
        if (tpl.pattern && tpl.pattern.length > 0) {
            const sections = templatePatternToSections(tpl.pattern);
            setSections(sections);
            // Set total marks from template
            const total = tpl.pattern.reduce((s, p) => s + p.num_parts * p.marks_per_part, 0);
            setTotalMarks(total);
        }
    };

    return (
        <div className="space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground px-1">
                Use Template
            </p>
            <div className="space-y-1.5">
                {templates.map((tpl) => {
                    const isSelected = selectedTemplate?.template_id === tpl.template_id;
                    const patternSummary = tpl.pattern?.map(
                        (p) => `Q${p.question_num}: ${p.num_parts}×${p.marks_per_part}M`
                    ).join(" | ") ?? "No pattern";

                    return (
                        <button
                            key={tpl.template_id}
                            disabled={disabled}
                            onClick={() => handleSelectTemplate(tpl)}
                            className={cn(
                                "w-full flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-all duration-150 group",
                                isSelected
                                    ? "border-emerald-500/50 bg-emerald-500/8 shadow-sm"
                                    : "border-border/50 bg-muted/20 hover:border-primary/30 hover:bg-primary/5",
                                disabled && "opacity-50 cursor-not-allowed"
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
                                <p className="text-[10px] text-muted-foreground truncate">{patternSummary}</p>
                            </div>

                            {isSelected ? (
                                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 flex-shrink-0" />
                            ) : (
                                <ChevronRight className="h-3 w-3 text-muted-foreground/40 flex-shrink-0 group-hover:text-primary" />
                            )}
                        </button>
                    );
                })}
            </div>

            {selectedTemplate && (
                <p className="text-[10px] text-emerald-600 font-bold px-1 flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Pattern autofilled from &quot;{selectedTemplate.name}&quot;
                </p>
            )}
        </div>
    );
}
