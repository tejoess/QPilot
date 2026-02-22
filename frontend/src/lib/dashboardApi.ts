/**
 * lib/dashboardApi.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * API helpers for Dashboard data.
 * 
 * NOTE: These routes are NOT currently defined in FRONTEND_INTEGRATION_GUIDE.md.
 * They are implemented as stubs using localStorage or static data to ensure 
 * the Dashboard is fully functional and visually accurate for the demo.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { Project } from "@/types/api";
import { SystemStats } from "@/store/dashboardStore";

const delay = (ms = 800) => new Promise((r) => setTimeout(r, ms));

export async function getSystemStats(): Promise<SystemStats> {
    await delay(1000); // Simulate network latency

    // Static demonstration data
    return {
        totalPapers: 1248,
        lastGenTime: "2 mins ago",
        avgGenTime: "45 seconds",
        pyqDbSize: "15,000+ Questions",
        trends: {
            totalPapers: "+12% this month"
        }
    };
}

export async function getRecentPapers(): Promise<Project[]> {
    await delay(1200);

    // Try to read from projectApi's localStorage key if it exists
    const LS_PROJECTS_KEY = "qpilot_projects_v2";
    try {
        const raw = localStorage.getItem(LS_PROJECTS_KEY);
        if (raw) {
            const projects = JSON.parse(raw) as Project[];
            return projects.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
        }
    } catch (e) {
        console.warn("Failed to read recent papers from localStorage", e);
    }

    // Fallback demo data
    return [
        {
            id: "p1",
            name: "Mid-Term Math Exam",
            subject: "Mathematics",
            grade: "10",
            board: "CBSE",
            paperType: "cbse",
            totalMarks: 80,
            duration: "3 Hours",
            instructions: "All questions are compulsory.",
            status: "done",
            settings: { includeAnswerKey: true, shuffleQuestions: false, negativeMarking: false, difficultyDistribution: [30, 40, 30] },
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
        },
        {
            id: "p2",
            name: "Unit Test - Physics",
            subject: "Physics",
            grade: "12",
            board: "ICSE",
            paperType: "icse",
            totalMarks: 40,
            duration: "1.5 Hours",
            instructions: "Carry your own calculator.",
            status: "draft",
            settings: { includeAnswerKey: true, shuffleQuestions: true, negativeMarking: true, difficultyDistribution: [20, 50, 30] },
            createdAt: new Date(Date.now() - 86400000).toISOString(),
            updatedAt: new Date(Date.now() - 3600000).toISOString(),
        }
    ];
}
