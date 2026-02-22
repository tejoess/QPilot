import { db } from '@/index';
import { qpMetadataTable } from '@/db/schema';
import { eq } from 'drizzle-orm';
import { NextResponse } from 'next/server';

export async function GET(
    request: Request,
    { params }: { params: { id: string } }
) {
    try {
        const { id } = await params;
        const result = await db.select().from(qpMetadataTable).where(eq(qpMetadataTable.id, id)).limit(1);

        if (result.length === 0) {
            return NextResponse.json({ error: 'Metadata not found' }, { status: 404 });
        }

        return NextResponse.json(result[0]);
    } catch (error) {
        console.error('Error fetching qp_metadata:', error);
        return NextResponse.json({ error: 'Failed to fetch metadata' }, { status: 500 });
    }
}
