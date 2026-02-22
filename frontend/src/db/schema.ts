import { pgTable, text, timestamp, varchar, uuid, integer } from 'drizzle-orm/pg-core';

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
