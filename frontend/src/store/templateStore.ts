/**
 * store/templateStore.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * Zustand store for the DOCX Template management module.
 * Tracks uploaded templates, the selected template for paper generation,
 * and the render state.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface TemplatePattern {
    question_num: number;
    parts: string[];
    num_parts: number;
    marks_per_part: number;
}

export interface UploadedTemplate {
    template_id: string;
    name: string;
    pattern: TemplatePattern[];
    placeholders: string[];
}

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

interface TemplateState {
    templates: UploadedTemplate[];
    selectedTemplate: UploadedTemplate | null;
    isUploading: boolean;
    isRendering: boolean;
    userId: string;

    // Actions
    setUserId: (id: string) => void;
    setTemplates: (templates: UploadedTemplate[]) => void;
    selectTemplate: (template: UploadedTemplate | null) => void;
    fetchTemplates: () => Promise<void>;
    uploadTemplate: (file: File) => Promise<UploadedTemplate | null>;
    renderPaper: (
        paperJson: object,
        metadata: {
            subject: string;
            class_name: string;
            marks: string;
            date: string;
            duration: string;
            exam_name: string;
            project_id?: string;
        }
    ) => Promise<void>;
    deleteTemplate: (templateId: string) => Promise<void>;
}

export const useTemplateStore = create<TemplateState>()(
    persist<TemplateState>(
        (set, get) => ({
            templates: [],
            selectedTemplate: null,
            isUploading: false,
            isRendering: false,
            userId: "anonymous",

            setUserId: (id: string) => set({ userId: id }),

            setTemplates: (templates: UploadedTemplate[]) => set({ templates }),

            selectTemplate: (template: UploadedTemplate | null) => set({ selectedTemplate: template }),

            fetchTemplates: async () => {
                const { userId } = get();
                try {
                    const res = await fetch(`${BACKEND_URL}/templates/list?user_id=${encodeURIComponent(userId)}`);
                    if (!res.ok) return;
                    const data = await res.json();
                    set({ templates: data.templates || [] });
                } catch (err) {
                    console.error("Failed to fetch templates:", err);
                }
            },

            uploadTemplate: async (file: File): Promise<UploadedTemplate | null> => {
                const { userId } = get();
                set({ isUploading: true });
                try {
                    const form = new FormData();
                    form.append("file", file);
                    form.append("user_id", userId);

                    const res = await fetch(`${BACKEND_URL}/templates/upload`, {
                        method: "POST",
                        body: form,
                    });

                    if (!res.ok) {
                        const err = await res.json();
                        throw new Error(err.detail || "Upload failed");
                    }

                    const data = await res.json();
                    const newTemplate: UploadedTemplate = {
                        template_id: data.template_id,
                        name: data.name,
                        pattern: data.pattern,
                        placeholders: data.placeholders?.all || [],
                    };

                    set((state) => ({
                        templates: [...state.templates, newTemplate],
                        isUploading: false,
                    }));

                    return newTemplate;
                } catch (err) {
                    console.error("Upload error:", err);
                    set({ isUploading: false });
                    return null;
                }
            },

            renderPaper: async (paperJson: object, metadata: {
                subject: string;
                class_name: string;
                marks: string;
                date: string;
                duration: string;
                exam_name: string;
                project_id?: string;
            }) => {
                const { selectedTemplate, userId } = get();
                if (!selectedTemplate) return;

                set({ isRendering: true });
                try {
                    const form = new FormData();
                    form.append("template_id", selectedTemplate.template_id);
                    form.append("user_id", userId);
                    form.append("paper_json", JSON.stringify(paperJson));
                    form.append("subject", metadata.subject);
                    form.append("class_name", metadata.class_name);
                    form.append("marks", metadata.marks);
                    form.append("date", metadata.date);
                    form.append("duration", metadata.duration);
                    form.append("exam_name", metadata.exam_name);
                    if (metadata.project_id) {
                        form.append("project_id", metadata.project_id);
                    }

                    const res = await fetch(`${BACKEND_URL}/templates/render`, {
                        method: "POST",
                        body: form,
                    });

                    if (!res.ok) {
                        const err = await res.json();
                        throw new Error(err.detail || "Render failed");
                    }

                    // Download the returned DOCX
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    const examName = metadata.exam_name || "exam";
                    a.href = url;
                    a.download = `question_paper_${examName.replace(/\s+/g, "_")}.docx`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    URL.revokeObjectURL(url);
                } catch (err) {
                    console.error("Render error:", err);
                    throw err;
                } finally {
                    set({ isRendering: false });
                }
            },

            deleteTemplate: async (templateId: string) => {
                const { userId } = get();
                try {
                    const res = await fetch(`${BACKEND_URL}/templates/delete?template_id=${templateId}&user_id=${encodeURIComponent(userId)}`, {
                        method: "DELETE"
                    });
                    if (res.ok) {
                        set(state => ({
                            templates: state.templates.filter(t => t.template_id !== templateId),
                            selectedTemplate: state.selectedTemplate?.template_id === templateId ? null : state.selectedTemplate
                        }));
                    }
                } catch (err) {
                    console.error("Failed to delete template:", err);
                }
            },
        }),
        {
            name: "qpilot-templates",
            partialize: (state) => ({
                templates: state.templates,
                userId: state.userId,
            }) as unknown as TemplateState,
        }
    )
);

/** Converts a TemplatePattern[] into the format PaperPatternAgentCard sections use */
export function templatePatternToSections(pattern: TemplatePattern[]) {
    return pattern.map((p, i) => ({
        id: crypto.randomUUID(),
        name: `Q${p.question_num}`,
        type: p.num_parts > 2 ? "short_answer" : "long_answer",
        numQuestions: p.num_parts,
        marksPerQuestion: p.marks_per_part,
        totalMarks: p.num_parts * p.marks_per_part,
    }));
}
