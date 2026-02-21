/**
 * types/api.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * All types here are derived STRICTLY from FRONTEND_INTEGRATION_GUIDE.md.
 *
 * Defined in the guide (Section 2 & 12):
 *   POST /generate-paper  →  PaperGenerationRequest / PaperGenerationResponse
 *   WS   /ws/{session_id}
 *
 * NOT in the guide (no backend route exists):
 *   Project CRUD, Section CRUD → modelled as local stubs below.
 *   These are clearly marked and can be wired to real endpoints by updating
 *   lib/projectApi.ts only.
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ─── Defined in FRONTEND_INTEGRATION_GUIDE.md ────────────────────────────────

/** POST /generate-paper  –  request body */
export interface PaperGenerationRequest {
    subject: string;
    grade: string;
    board: string;
}

/** POST /generate-paper  –  response body */
export interface PaperGenerationResponse {
    status: "success" | "error";
    file_path: string;
}

// ─── Domain types (NOT in guide – frontend stubs) ─────────────────────────────

export type ProjectStatus = "draft" | "processing" | "done" | "error";

export type PaperType = "cbse" | "icse" | "state";

/** Represents a single exam-paper project */
export interface Project {
    id: string;
    name: string;
    subject: string;
    grade: string;
    board: string;            // maps to PaperGenerationRequest.board
    paperType: PaperType;
    totalMarks: number;    // Added: Total paper marks
    duration: string;      // Added: Duration of the exam
    instructions: string;  // Added: Instructions for candidates
    status: ProjectStatus;
    settings: GenerationSettings; // Added: Switches and difficulty
    createdAt: string;
    updatedAt: string;
}

export interface GenerationSettings {
    includeAnswerKey: boolean;
    shuffleQuestions: boolean;
    negativeMarking: boolean;
    difficultyDistribution: number[]; // e.g. [30, 40, 30] for Easy, Medium, Hard
}

export type SectionType =
    | "mcq"
    | "short_answer"
    | "long_answer"
    | "fill_in_the_blank"
    | "true_false";

export type DifficultyLevel = "easy" | "medium" | "hard";

/** Represents a section inside a project */
export interface Section {
    id: string;
    projectId: string;
    name: string;
    type: SectionType;
    numQuestions: number;      // Added
    marksPerQuestion: number;  // Added
    totalMarks: number;        // Computed: numQuestions * marksPerQuestion
    difficulty: DifficultyLevel; // Added
    order: number;
}

/** Payload for creating a new section */
export type CreateSectionPayload = Omit<Section, "id" | "projectId" | "totalMarks">;

/** Payload for updating a section */
export type UpdateSectionPayload = Partial<CreateSectionPayload>;

/** Payload for updating project metadata */
export type UpdateProjectPayload = Partial<Omit<Project, "id" | "createdAt" | "updatedAt" | "status">>;
