"use server";

import { db } from "@/index";
import { projectsTable, documentsTable, pipelineDataTable } from "@/db/schema";
import { eq, desc, and, inArray } from "drizzle-orm";
import { currentUser } from "@clerk/nextjs/server";
import { BlobServiceClient } from '@azure/storage-blob';

export async function getUserProjects() {
    const user = await currentUser();
    if (!user) return [];

    try {
        // Fetch all projects. We'll join documents in a second step or with a broader join
        const projects = await db
            .select()
            .from(projectsTable)
            .where(eq(projectsTable.userId, user.id))
            .orderBy(desc(projectsTable.createdAt))
            .limit(10);

        if (projects.length === 0) return [];

        const projectIds = projects.map(p => p.id);

        // Fetch all documents for these projects
        const docs = await db
            .select()
            .from(documentsTable)
            .where(and(
                inArray(documentsTable.projectId, projectIds),
                inArray(documentsTable.docType, ["final_pdf", "docx_paper"])
            ));

        // Map them back
        return projects.map(p => {
            // Find the best URL (prefer docx if it exists)
            const pDocs = docs.filter(d => d.projectId === p.id);
            const docx = pDocs.find(d => d.docType === "docx_paper");
            const pdf = pDocs.find(d => d.docType === "final_pdf");
            
            return {
                ...p,
                pdfUrl: docx?.azureUrl || pdf?.azureUrl || null
            };
        });
    } catch (e) {
        console.error("DB Error:", e);
        return [];
    }
}

export async function deleteProjectFromDb(projectId: string) {
    const user = await currentUser();
    if (!user) throw new Error("Unauthorized");

    try {
        // Delete all azure docs first
        const docs = await db.select().from(documentsTable).where(eq(documentsTable.projectId, projectId));
        const connStr = process.env.AZURE_STORAGE_CONNECTION_STRING;
        if (connStr) {
            const blobServiceClient = BlobServiceClient.fromConnectionString(connStr);
            for (const doc of docs) {
                if (doc.azureUrl) {
                    try {
                        const urlObj = new URL(doc.azureUrl);
                        const pathParts = urlObj.pathname.split('/').filter(Boolean);
                        if (pathParts.length >= 2) {
                            const containerClient = blobServiceClient.getContainerClient(pathParts[0]);
                            await containerClient.getBlobClient(pathParts.slice(1).join('/')).deleteIfExists();
                        }
                    } catch(err) { console.error("Azure doc delete err", err); }
                }
            }
        }
        await db.delete(documentsTable).where(eq(documentsTable.projectId, projectId));
        await db.delete(pipelineDataTable).where(eq(pipelineDataTable.projectId, projectId));
        await db.delete(projectsTable).where(eq(projectsTable.id, projectId));
        return true;
    } catch (e) {
        console.error("Delete DB Error:", e);
        return false;
    }
}


export async function deleteDocumentAndBlob(id: number, azureUrl: string) {
    const user = await currentUser();
    if (!user) return false;

    try {
        await db.delete(documentsTable).where(and(eq(documentsTable.id, id), eq(documentsTable.userId, user.id)));
        
        const connStr = process.env.AZURE_STORAGE_CONNECTION_STRING;
        if (connStr && azureUrl) {
            const blobServiceClient = BlobServiceClient.fromConnectionString(connStr);
            const urlObj = new URL(azureUrl);
            const pathParts = urlObj.pathname.split('/').filter(Boolean);
            if (pathParts.length >= 2) {
                const containerName = pathParts[0];
                const blobName = pathParts.slice(1).join('/');
                const containerClient = blobServiceClient.getContainerClient(containerName);
                const blobClient = containerClient.getBlobClient(blobName);
                await blobClient.deleteIfExists();
                console.log(`Deleted Azure blob: ${blobName}`);
            }
        }
        return true;
    } catch (e: any) {
        console.error("Delete Doc Error:", e);
        return false;
    }
}

export async function getUserDocuments() {
    const user = await currentUser();
    if (!user) return [];

    try {
        const docs = await db
            .select()
            .from(documentsTable)
            .where(eq(documentsTable.userId, user.id))
            .orderBy(desc(documentsTable.createdAt));
            
        return docs.map(d => {
            let label = d.docType || "Document";
            if (label === "syllabus") label = "Syllabus";
            else if (label === "pyqs") label = "PYQ Upload";
            else if (label === "answer_key") label = "Answer Key";
            else if (label === "final_pdf") label = "Generated PDF";
            else if (label === "template") label = "DOCX Template";
            else if (label === "docx_paper") label = "Generated DOCX";
            
            return {
                id: d.id,
                name: d.name,
                type: label,
                date: d.createdAt.toLocaleDateString(),
                size: d.fileSizeBytes ? `${(d.fileSizeBytes / 1024 / 1024).toFixed(1)} MB` : "—",
                url: d.azureUrl
            };
        });
    } catch (e) {
        console.error("DB Error:", e);
        return [];
    }
}
