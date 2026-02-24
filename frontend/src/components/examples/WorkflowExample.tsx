/**
 * EXAMPLE: How to Use the WebSocket Integration
 * ─────────────────────────────────────────────────────────────────────────────
 * This file demonstrates how to use the new orchestration system in your
 * existing components (SyllabusAgentCard, PyqAgentCard, TeacherInputAgentCard).
 * ─────────────────────────────────────────────────────────────────────────────
 */

"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { useWorkflowOrchestrator } from "@/hooks/useWorkflowOrchestrator";
import { WebSocketLogPanel } from "@/components/processing/WebSocketLogPanel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Upload, FileText, Loader2 } from "lucide-react";

export function WorkflowExample() {
    const orchestrator = useWorkflowOrchestrator();
    
    const [syllabusText, setSyllabusText] = useState("");
    const [syllabusFile, setSyllabusFile] = useState<File | null>(null);
    
    const [pyqsText, setPyqsText] = useState("");
    const [pyqsFile, setPyqsFile] = useState<File | null>(null);
    
    const [teacherInput, setTeacherInput] = useState("");
    const [totalMarks, setTotalMarks] = useState(80);
    const [totalQuestions, setTotalQuestions] = useState(25);

    // ─── Step 1: Analyze Syllabus ─────────────────────────────────────────────

    const handleSyllabusAnalysis = async () => {
        try {
            await orchestrator.analyzeSyllabus({
                file: syllabusFile || undefined,
                text: syllabusText || undefined,
            });
            
            // Queue PYQs analysis to run after this completes
            orchestrator.queuePyqsAfterSyllabus();
            
            console.log("✅ Syllabus analysis started!");
        } catch (error) {
            console.error("Failed to analyze syllabus:", error);
        }
    };

    // ─── Step 2: Analyze PYQs ─────────────────────────────────────────────────

    const handlePyqsAnalysis = async () => {
        if (!orchestrator.syllabusSessionId) {
            alert("Please analyze syllabus first!");
            return;
        }

        try {
            await orchestrator.analyzePyqs({
                file: pyqsFile || undefined,
                text: pyqsText || undefined,
            });

            console.log("✅ PYQs analysis started!");
        } catch (error) {
            console.error("Failed to analyze PYQs:", error);
        }
    };

    // ─── Step 3: Generate Paper ───────────────────────────────────────────────

    const handlePaperGeneration = async () => {
        if (!orchestrator.syllabusSessionId || !orchestrator.pyqsSessionId) {
            alert("Please complete syllabus and PYQs analysis first!");
            return;
        }

        try {
            await orchestrator.generatePaper({
                totalMarks,
                totalQuestions,
                teacherInput: teacherInput || undefined,
                bloomLevels: {
                    remember: 20,
                    understand: 30,
                    apply: 30,
                    analyze: 20,
                },
            });

            console.log("✅ Paper generation started!");
        } catch (error) {
            console.error("Failed to generate paper:", error);
        }
    };

    // ─── Auto-run All Steps ───────────────────────────────────────────────────

    const handleRunAll = async () => {
        try {
            // Queue all steps
            orchestrator.queuePyqsAfterSyllabus();
            orchestrator.queuePaperAfterPyqs();

            // Start with syllabus
            await handleSyllabusAnalysis();

            // The rest will auto-trigger!
        } catch (error) {
            console.error("Workflow failed:", error);
        }
    };

    return (
        <div className="container mx-auto p-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left Column: Inputs */}
                <div className="space-y-6">
                    {/* Step 1: Syllabus */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <FileText className="h-5 w-5" />
                                Step 1: Syllabus Analysis
                            </CardTitle>
                            <CardDescription>
                                Upload PDF or paste text
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <Input
                                type="file"
                                accept=".pdf"
                                onChange={(e) => setSyllabusFile(e.target.files?.[0] || null)}
                            />
                            <Textarea
                                placeholder="Or paste syllabus text here..."
                                value={syllabusText}
                                onChange={(e) => setSyllabusText(e.target.value)}
                                rows={4}
                            />
                            <Button
                                onClick={handleSyllabusAnalysis}
                                disabled={orchestrator.syllabusStatus === "running"}
                                className="w-full"
                            >
                                {orchestrator.syllabusStatus === "running" ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Analyzing...
                                    </>
                                ) : (
                                    <>
                                        <Upload className="mr-2 h-4 w-4" />
                                        Analyze Syllabus
                                    </>
                                )}
                            </Button>
                            {orchestrator.syllabusStatus === "completed" && (
                                <p className="text-sm text-green-600">
                                    ✅ Completed • Session: {orchestrator.syllabusSessionId?.slice(0, 8)}...
                                </p>
                            )}
                        </CardContent>
                    </Card>

                    {/* Step 2: PYQs */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <FileText className="h-5 w-5" />
                                Step 2: PYQs Analysis
                            </CardTitle>
                            <CardDescription>
                                Upload PDF or paste questions
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <Input
                                type="file"
                                accept=".pdf"
                                onChange={(e) => setPyqsFile(e.target.files?.[0] || null)}
                                disabled={!orchestrator.syllabusSessionId}
                            />
                            <Textarea
                                placeholder="Or paste PYQ text here..."
                                value={pyqsText}
                                onChange={(e) => setPyqsText(e.target.value)}
                                rows={4}
                                disabled={!orchestrator.syllabusSessionId}
                            />
                            <Button
                                onClick={handlePyqsAnalysis}
                                disabled={
                                    !orchestrator.syllabusSessionId ||
                                    orchestrator.pyqsStatus === "running"
                                }
                                className="w-full"
                            >
                                {orchestrator.pyqsStatus === "running" ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Analyzing...
                                    </>
                                ) : (
                                    <>
                                        <Upload className="mr-2 h-4 w-4" />
                                        Analyze PYQs
                                    </>
                                )}
                            </Button>
                            {orchestrator.pyqsStatus === "completed" && (
                                <p className="text-sm text-green-600">
                                    ✅ Completed • Session: {orchestrator.pyqsSessionId?.slice(0, 8)}...
                                </p>
                            )}
                        </CardContent>
                    </Card>

                    {/* Step 3: Generate */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <FileText className="h-5 w-5" />
                                Step 3: Generate Paper
                            </CardTitle>
                            <CardDescription>
                                Configure and generate
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-sm font-medium">Total Marks</label>
                                    <Input
                                        type="number"
                                        value={totalMarks}
                                        onChange={(e) => setTotalMarks(Number(e.target.value))}
                                    />
                                </div>
                                <div>
                                    <label className="text-sm font-medium">Total Questions</label>
                                    <Input
                                        type="number"
                                        value={totalQuestions}
                                        onChange={(e) => setTotalQuestions(Number(e.target.value))}
                                    />
                                </div>
                            </div>
                            <Textarea
                                placeholder="Teacher input (optional)..."
                                value={teacherInput}
                                onChange={(e) => setTeacherInput(e.target.value)}
                                rows={3}
                            />
                            <Button
                                onClick={handlePaperGeneration}
                                disabled={
                                    !orchestrator.syllabusSessionId ||
                                    !orchestrator.pyqsSessionId ||
                                    orchestrator.paperStatus === "running"
                                }
                                className="w-full"
                            >
                                {orchestrator.paperStatus === "running" ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Generating...
                                    </>
                                ) : (
                                    <>
                                        <FileText className="mr-2 h-4 w-4" />
                                        Generate Paper
                                    </>
                                )}
                            </Button>
                        </CardContent>
                    </Card>

                    {/* Run All Button */}
                    <Button
                        onClick={handleRunAll}
                        variant="default"
                        size="lg"
                        className="w-full"
                        disabled={orchestrator.syllabusStatus === "running"}
                    >
                        🚀 Run Complete Workflow
                    </Button>
                </div>

                {/* Right Column: Logs */}
                <div className="lg:sticky lg:top-6 h-[calc(100vh-8rem)]">
                    <WebSocketLogPanel />
                </div>
            </div>
        </div>
    );
}
