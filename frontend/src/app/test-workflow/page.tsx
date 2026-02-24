/**
 * app/test-workflow/page.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Test page for WebSocket workflow integration
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { WorkflowExample } from "@/components/examples/WorkflowExample";

export default function TestWorkflowPage() {
    return (
        <div className="min-h-screen bg-background">
            <div className="border-b">
                <div className="container mx-auto p-4">
                    <h1 className="text-2xl font-bold">WebSocket Workflow Test</h1>
                    <p className="text-sm text-muted-foreground">
                        Test the 3-step question paper generation workflow with real-time updates
                    </p>
                </div>
            </div>
            <WorkflowExample />
        </div>
    );
}
