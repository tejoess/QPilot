import { db } from '@/index';
import { qpMetadataTable } from '@/db/schema';
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const { exam_title, subject, grade, total_marks, duration, instructions } = body;

        const result = await db.insert(qpMetadataTable).values({
            examTitle: exam_title,
            subject,
            grade,
            totalMarks: parseInt(total_marks),
            duration,
            instructions,
        }).returning();

        return NextResponse.json(result[0]);
    } catch (error) {
        console.error('Error inserting qp_metadata:', error);
        return NextResponse.json({ error: 'Failed to insert metadata' }, { status: 500 });
    }
}
