import { pgTable, text, timestamp, varchar, uuid, integer, json, serial } from 'drizzle-orm/pg-core';

export const usersTable = pgTable('users', {
    clerkId: varchar('clerk_id', { length: 255 }).primaryKey().notNull(),
    name: text('name').notNull(),
    email: text('email').notNull(),
    createdAt: timestamp('created_at').defaultNow().notNull(),
    updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export const qpMetadataTable = pgTable('qp_metadata', {
    id: uuid('id').defaultRandom().primaryKey(),
    examTitle: text('exam_title').notNull(),
    subject: text('subject').notNull(),
    grade: text('grade').notNull(),
    totalMarks: integer('total_marks').notNull(),
    duration: text('duration').notNull(),
    instructions: text('instructions'),
    createdAt: timestamp('created_at').defaultNow().notNull(),
});

export const projectsTable = pgTable('projects', {
    id: varchar('id', { length: 255 }).primaryKey().notNull(), // proj-xyz
    userId: varchar('user_id', { length: 255 }).references(() => usersTable.clerkId).notNull(),
    name: text('name').notNull(),
    subject: text('subject'),
    grade: text('grade'),
    totalMarks: integer('total_marks'),
    duration: text('duration'),
    status: text('status').default('draft'),
    settings: json('settings'),
    createdAt: timestamp('created_at').defaultNow().notNull(),
    updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export const pipelineDataTable = pgTable('pipeline_data', {
    id: serial('id').primaryKey(),
    projectId: varchar('project_id', { length: 255 }).references(() => projectsTable.id).unique().notNull(),
    syllabusJson: json('syllabus_json'),
    knowledgeGraphJson: json('knowledge_graph_json'),
    pyqsJson: json('pyqs_json'),
    blueprintJson: json('blueprint_json'),
    blueprintVerificationJson: json('blueprint_verification_json'),
    paperMetadataJson: json('paper_metadata_json'),
    draftPaperJson: json('draft_paper_json'),
    finalPaperJson: json('final_paper_json'),
    answerKeyJson: json('answer_key_json'),
    createdAt: timestamp('created_at').defaultNow().notNull(),
});

export const documentsTable = pgTable('documents', {
    id: serial('id').primaryKey(),
    userId: varchar('user_id', { length: 255 }).references(() => usersTable.clerkId).notNull(),
    projectId: varchar('project_id', { length: 255 }).references(() => projectsTable.id), // Optional link
    name: text('name').notNull(),
    docType: text('doc_type').notNull(), // syllabus, pyq, template, final_pdf, answer_key_pdf
    azureUrl: text('azure_url').notNull(),
    fileSizeBytes: integer('file_size_bytes'),
    createdAt: timestamp('created_at').defaultNow().notNull(),
});
