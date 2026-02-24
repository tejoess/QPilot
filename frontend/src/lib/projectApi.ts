/**
 * lib/projectApi.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * API helpers for Project and Section CRUD.
 *
 * INTEGRATION GUIDE STATUS:
 *   The FRONTEND_INTEGRATION_GUIDE.md defines only TWO backend endpoints:
 *     • POST /generate-paper   (paper generation)
 *     • WS   /ws/{session_id}  (real-time logs)
 *
 *   No Project or Section CRUD routes are defined in the guide.
 *
 *   This module implements those operations using localStorage so the Builder
 *   page is fully functional today inhabitants. The data shapes are designed to be 1:1
 *   compatible with a REST API. To connect a real backend:
 *
 *   1. Replace each stub function body with an apiFetch() call.
 *   2. The ONLY real backend call on this page is generatePaper().
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { apiFetch } from "@/lib/apiClient";
import type {
    Project,
    Section,
    CreateSectionPayload,
    UpdateSectionPayload,
    UpdateProjectPayload,
    PaperGenerationRequest,
    PaperGenerationResponse,
} from "@/types/api";

const LS_PROJECTS_KEY = "qpilot_projects_v2"; // Versioned to avoid old data conflicts
const LS_SECTIONS_KEY = "qpilot_sections_v2";

const DEFAULT_SETTINGS = {
    includeAnswerKey: true,
    shuffleQuestions: false,
    negativeMarking: false,
    difficultyDistribution: [30, 40, 30],
};

function readProjects(): Project[] {
    try {
        const raw = localStorage.getItem(LS_PROJECTS_KEY);
        return raw ? (JSON.parse(raw) as Project[]) : seedProjects();
    } catch {
        return seedProjects();
    }
}

function writeProjects(projects: Project[]): void {
    localStorage.setItem(LS_PROJECTS_KEY, JSON.stringify(projects));
}

function readSections(): Section[] {
    try {
        const raw = localStorage.getItem(LS_SECTIONS_KEY);
        return raw ? (JSON.parse(raw) as Section[]) : seedSections();
    } catch {
        return seedSections();
    }
}

function writeSections(sections: Section[]): void {
    localStorage.setItem(LS_SECTIONS_KEY, JSON.stringify(sections));
}

function now(): string {
    return new Date().toISOString();
}

function uuid(): string {
    return crypto.randomUUID();
}

function seedProjects(): Project[] {
    const projects: Project[] = [
        {
            id: "proj-demo-1",
            name: "Terminal Exam 2026",
            subject: "Mathematics",
            grade: "10",
            board: "CBSE",
            paperType: "cbse",
            totalMarks: 80,
            duration: "3 Hours",
            instructions: "All questions are compulsory.\nUse of calculator is not allowed.",
            status: "draft",
            settings: DEFAULT_SETTINGS,
            createdAt: now(),
            updatedAt: now(),
        },
    ];
    writeProjects(projects);
    return projects;
}

function seedSections(): Section[] {
    const sections: Section[] = [
        {
            id: "sec-1",
            projectId: "proj-demo-1",
            name: "Section A: Multiple Choice",
            type: "mcq",
            numQuestions: 20,
            marksPerQuestion: 1,
            totalMarks: 20,
            difficulty: "easy",
            order: 1,
        },
        {
            id: "sec-2",
            projectId: "proj-demo-1",
            name: "Section B: Short Answer",
            type: "short_answer",
            numQuestions: 10,
            marksPerQuestion: 2,
            totalMarks: 20,
            difficulty: "medium",
            order: 2,
        },
        {
            id: "sec-3",
            projectId: "proj-demo-1",
            name: "Section C: Long Answer",
            type: "long_answer",
            numQuestions: 8,
            marksPerQuestion: 5,
            totalMarks: 40,
            difficulty: "hard",
            order: 3,
        },
    ];
    writeSections(sections);
    return sections;
}

const delay = (ms = 500) => new Promise((r) => setTimeout(r, ms));

export async function getProject(id: string): Promise<Project> {
    await delay(600);
    const project = readProjects().find((p) => p.id === id);
    if (!project) throw new Error(`Project "${id}" not found.`);
    return { ...project };
}

export async function updateProject(
    id: string,
    payload: UpdateProjectPayload
): Promise<Project> {
    await delay(700);
    const projects = readProjects();
    const idx = projects.findIndex((p) => p.id === id);
    if (idx === -1) throw new Error(`Project "${id}" not found.`);

    // Merge settings carefully if present
    const updatedProject = {
        ...projects[idx],
        ...payload,
        settings: payload.settings ? { ...projects[idx].settings, ...payload.settings } : projects[idx].settings,
        updatedAt: now()
    };

    projects[idx] = updatedProject;
    writeProjects(projects);
    return { ...projects[idx] };
}

export async function getSections(projectId: string): Promise<Section[]> {
    await delay(500);
    return readSections()
        .filter((s) => s.projectId === projectId)
        .sort((a, b) => a.order - b.order);
}

export async function addSection(
    projectId: string,
    payload: CreateSectionPayload
): Promise<Section> {
    await delay(600);
    const existing = readSections().filter((s) => s.projectId === projectId);
    const section: Section = {
        id: uuid(),
        projectId,
        name: payload.name,
        type: payload.type,
        numQuestions: payload.numQuestions,
        marksPerQuestion: payload.marksPerQuestion,
        totalMarks: payload.numQuestions * payload.marksPerQuestion, // Compute
        difficulty: payload.difficulty,
        order: payload.order ?? existing.length + 1,
    };
    const all = readSections();
    all.push(section);
    writeSections(all);
    return { ...section };
}

export async function updateSection(
    _projectId: string,
    sectionId: string,
    payload: UpdateSectionPayload
): Promise<Section> {
    await delay(600);
    const all = readSections();
    const idx = all.findIndex((s) => s.id === sectionId);
    if (idx === -1) throw new Error(`Section "${sectionId}" not found.`);

    const updated = { ...all[idx], ...payload };
    // Re-calculate totalMarks if qty or marks changed
    updated.totalMarks = updated.numQuestions * updated.marksPerQuestion;

    all[idx] = updated;
    writeSections(all);
    return { ...all[idx] };
}

export async function deleteSection(
    _projectId: string,
    sectionId: string
): Promise<void> {
    await delay(500);
    const all = readSections().filter((s) => s.id !== sectionId);
    writeSections(all);
}

export async function generatePaper(
    data: PaperGenerationRequest
): Promise<PaperGenerationResponse> {
    // STRICTLY follow the guide for the payload
    return apiFetch<PaperGenerationResponse>("/generate-paper", {
        method: "POST",
        json: data,
    });
}

/**
 * SYLLABUS AGENT ROUTES (Integration Guide Placeholder)
 */

export interface SyllabusExtractRequest {
    projectId: string;
    sourceType: "pdf" | "text";
    content?: string;
    file?: File;
}

export async function extractSyllabus(data: SyllabusExtractRequest): Promise<{ status: string; jobId: string }> {
    // Integration Placeholder: POST /extract-syllabus
    // For now, simulate a successful trigger
    await delay(1000);
    return { status: "running", jobId: `syllabus-job-${data.projectId}` };
}

export async function getSyllabusStatus(jobId: string): Promise<{ status: string; currentStep: number }> {
    // Integration Placeholder: GET /syllabus-status/{jobId}
    // Simulate progression for the UI
    return apiFetch<{ status: string; currentStep: number }>(`/syllabus-status/${jobId}`).catch(() => {
        // Fallback for demo if route doesn't exist yet
        return { status: "running", currentStep: 1 };
    });
}

/**
 * PYQ AGENT ROUTES (Integration Guide Placeholder)
 */

export interface PyqExtractRequest {
    projectId: string;
    sourceType: "pdf" | "text";
    content?: string;
    year?: string;
    board?: string;
    file?: File;
}

export async function processPyqs(data: PyqExtractRequest): Promise<{ status: string; jobId: string }> {
    // Integration Placeholder: POST /process-pyqs
    await delay(1000);
    return { status: "running", jobId: `pyq-job-${data.projectId}` };
}

export async function getPyqStatus(jobId: string): Promise<{ status: string; currentStep: number }> {
    // Integration Placeholder: GET /pyq-status/{jobId}
    return apiFetch<{ status: string; currentStep: number }>(`/pyq-status/${jobId}`).catch(() => {
        return { status: "running", currentStep: 1 };
    });
}

/**
 * BLOOXANOMY AGENT ROUTES (Integration Guide Placeholder)
 */

export interface BloomDistributionRequest {
    projectId: string;
    levels: {
        remember: number;
        understand: number;
        apply: number;
        analyze: number;
        evaluate: number;
        create: number;
    };
}

export async function applyBloomDistribution(data: BloomDistributionRequest): Promise<{ status: string; jobId: string }> {
    // Integration Placeholder: POST /apply-bloom
    await delay(1000);
    return { status: "running", jobId: `bloom-job-${data.projectId}` };
}

export async function getBloomStatus(jobId: string): Promise<{ status: string; currentStep: number }> {
    // Integration Placeholder: GET /bloom-status/{jobId}
    return apiFetch<{ status: string; currentStep: number }>(`/bloom-status/${jobId}`).catch(() => {
        return { status: "running", currentStep: 1 };
    });
}

/**
 * PAPER PATTERN AGENT ROUTES (Integration Guide Placeholder)
 */

export interface PatternSectionInput {
    name: string;
    type: string;
    numQuestions: number;
    marksPerQuestion: number;
}

export interface PaperPatternRequest {
    projectId: string;
    sections: PatternSectionInput[];
}

export async function applyPaperPattern(data: PaperPatternRequest): Promise<{ status: string; jobId: string }> {
    // Integration Placeholder: POST /apply-pattern
    await delay(1000);
    return { status: "running", jobId: `pattern-job-${data.projectId}` };
}

export async function getPatternStatus(jobId: string): Promise<{ status: string; currentStep: number }> {
    // Integration Placeholder: GET /pattern-status/{jobId}
    return apiFetch<{ status: string; currentStep: number }>(`/pattern-status/${jobId}`).catch(() => {
        return { status: "running", currentStep: 1 };
    });
}

/**
 * TEACHER INPUT & FINAL GENERATION (Integration Guide)
 */

export interface FinalGenerationRequest {
    projectId: string;
    teacherInput: string;
    // Note: Backend might also need subject/grade/board from the project context
}

export async function triggerFinalGeneration(data: FinalGenerationRequest): Promise<{ status: string; file_path: string }> {
    // Integration Placeholder: POST /generate-paper (Final Trigger)
    // According to the guide, this initiates the generation.
    await delay(1000);
    return { status: "success", file_path: "/path/to/generated/paper.pdf" };
}

// ─────────────────────────────────────────────────────────────────────────────
// ✨ NEW: Backend Integration APIs (Real Implementation)
// ─────────────────────────────────────────────────────────────────────────────

const BACKEND_URL = "http://127.0.0.1:8000";

/**
 * API 1: Analyze Syllabus
 * Accepts file OR text, returns session_id and parsed syllabus
 */
export interface AnalyzeSyllabusRequest {
    file?: File;
    text?: string;
    sessionId?: string; // Optional: for WebSocket tracking
}

export interface AnalyzeSyllabusResponse {
    status: "success" | "error";
    session_id: string;
    syllabus: {
        course_code: string;
        course_name: string;
        modules: Array<{
            module_number: string;
            module_name: string;
            weightage: number;
            topics: string[];
        }>;
    };
    message: string;
}

export async function analyzeSyllabus(request: AnalyzeSyllabusRequest): Promise<AnalyzeSyllabusResponse> {
    const formData = new FormData();
    
    if (request.file) {
        formData.append("file", request.file);
    }
    if (request.text) {
        formData.append("text", request.text);
    }
    if (request.sessionId) {
        formData.append("session_id", request.sessionId);
    }

    const response = await fetch(`${BACKEND_URL}/analyze-syllabus`, {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

/**
 * API 2: Analyze PYQs (Previous Year Questions)
 * Requires syllabus_session_id from step 1
 */
export interface AnalyzePyqsRequest {
    syllabusSessionId: string;
    file?: File;
    text?: string;
    sessionId?: string; // Optional: for WebSocket tracking
}

export interface AnalyzePyqsResponse {
    status: "success" | "error";
    session_id: string;
    pyqs: {
        questions: Array<{
            question_id: string;
            question_text: string;
            marks: number;
            difficulty: string;
            bloom_level: string;
            topic: string;
        }>;
    };
    total_questions: number;
    message: string;
}

export async function analyzePyqs(request: AnalyzePyqsRequest): Promise<AnalyzePyqsResponse> {
    const formData = new FormData();
    
    formData.append("syllabus_session_id", request.syllabusSessionId);
    
    if (request.file) {
        formData.append("file", request.file);
    }
    if (request.text) {
        formData.append("text", request.text);
    }
    if (request.sessionId) {
        formData.append("session_id", request.sessionId);
    }

    const response = await fetch(`${BACKEND_URL}/analyze-pyqs`, {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

/**
 * API 3: Generate Question Paper
 * Requires both syllabus_session_id and pyqs_session_id
 */
export interface GenerateQuestionPaperRequest {
    syllabusSessionId: string;
    pyqsSessionId: string;
    totalMarks?: number;
    totalQuestions?: number;
    // Bloom Taxonomy (percentages, must sum to 100)
    bloomLevels?: {
        remember?: number;
        understand?: number;
        apply?: number;
        analyze?: number;
        evaluate?: number;
        create?: number;
    };
    // Paper pattern (JSON structure)
    paperPattern?: {
        sections: Array<{
            name: string;
            type: string;
            numQuestions: number;
            marksPerQuestion: number;
        }>;
    };
    // Teacher input
    teacherInput?: string;
    // WebSocket tracking
    sessionId?: string;
}

export interface GenerateQuestionPaperResponse {
    status: "success" | "error";
    session_id: string;
    paper: {
        sections: Array<{
            section_name: string;
            questions: Array<{
                question_no: string;
                question_text: string;
                marks: number;
                difficulty: string;
                bloom_level: string;
            }>;
        }>;
    };
    verification: {
        verdict: string;
        rating: number;
    };
    pdf_path: string;
    message: string;
}

export async function generateQuestionPaper(
    request: GenerateQuestionPaperRequest
): Promise<GenerateQuestionPaperResponse> {
    const formData = new FormData();
    
    formData.append("syllabus_session_id", request.syllabusSessionId);
    formData.append("pyqs_session_id", request.pyqsSessionId);
    
    if (request.totalMarks !== undefined) {
        formData.append("total_marks", request.totalMarks.toString());
    }
    if (request.totalQuestions !== undefined) {
        formData.append("total_questions", request.totalQuestions.toString());
    }

    // Bloom taxonomy levels
    if (request.bloomLevels) {
        const { remember, understand, apply, analyze, evaluate, create } = request.bloomLevels;
        if (remember !== undefined) formData.append("bloom_remember", remember.toString());
        if (understand !== undefined) formData.append("bloom_understand", understand.toString());
        if (apply !== undefined) formData.append("bloom_apply", apply.toString());
        if (analyze !== undefined) formData.append("bloom_analyze", analyze.toString());
        if (evaluate !== undefined) formData.append("bloom_evaluate", evaluate.toString());
        if (create !== undefined) formData.append("bloom_create", create.toString());
    }

    // Paper pattern (transform keys to match backend expectations)
    if (request.paperPattern) {
        const transformedPattern = {
            sections: request.paperPattern.sections.map(section => ({
                section_name: section.name,
                section_description: section.type,
                question_count: section.numQuestions,
                marks_per_question: section.marksPerQuestion
            }))
        };
        console.log("📐 Transformed paper pattern:", transformedPattern);
        formData.append("paper_pattern", JSON.stringify(transformedPattern));
    }

    // Teacher input
    if (request.teacherInput) {
        formData.append("teacher_input", request.teacherInput);
    }

    // Session ID for WebSocket tracking
    if (request.sessionId) {
        formData.append("session_id", request.sessionId);
    }

    const response = await fetch(`${BACKEND_URL}/generate-paper`, {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}
