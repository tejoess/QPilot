"use client";

import { Button } from "@/components/ui/button";
import { Sparkles, PlayCircle } from "lucide-react";
import { useQPilotStore } from "@/store/qpilotStore";
import { useSyllabusStore } from "@/store/syllabusStore";
import { usePyqStore } from "@/store/pyqStore";
import { useBloomStore } from "@/store/bloomStore";
import { usePatternStore } from "@/store/patternStore";
import { useGenerationStore } from "@/store/generationStore";
import { cn } from "@/lib/utils";

export function AutoFillButton() {
    const { status, runAutoFillDemo, setActiveAgentIndex } = useQPilotStore();

    // External Store Actions
    const setSyllabusText = useSyllabusStore(s => s.setTextContent);
    const setPyqText = usePyqStore(s => s.setTextContent);
    const setPyqYear = usePyqStore(s => s.setYear);
    const setPyqBoard = usePyqStore(s => s.setBoard);
    const setBloomLevels = useBloomStore(s => s.setBloomLevels);
    const setPatternSections = usePatternStore(s => s.setSections);
    const setTargetMarks = usePatternStore(s => s.setTotalMarks);
    const setTeacherInput = useGenerationStore(s => s.setTeacherInput);

    // Resets
    const resetSyllabus = useSyllabusStore(s => s.reset);
    const resetPyq = usePyqStore(s => s.reset);
    const resetBloom = useBloomStore(s => s.reset);
    const resetPattern = usePatternStore(s => s.reset);
    const resetGeneration = useGenerationStore(s => s.reset);

    const handleDemo = () => {
        if (status !== "idle") return;

        // 1. Reset Stores and Trigger Orchestrator Logic
        resetSyllabus();
        resetPyq();
        resetBloom();
        resetPattern();
        resetGeneration();
        runAutoFillDemo();

        const teacherMsg = "Focus more on integration and avoid repeated PYQs. Add internal choices in Section C.";

        // 2. Populate Data Across Stores
        setSyllabusText("Unit 1: Limits and Derivatives\nUnit 2: Integration\nUnit 3: Differential Equations\nUnit 4: Applications of Integrals");

        setPyqText("Q1: Evaluate ∫x^2 dx\nQ2: Define limit.\nQ3: Solve dy/dx = x^2\nQ4: State Mean Value Theorem");
        setPyqYear("2024");
        setPyqBoard("CBSE");

        setBloomLevels({
            remember: 3,
            understand: 4,
            apply: 5,
            analyze: 4,
            evaluate: 2,
            create: 2
        });

        setTargetMarks(80);
        setPatternSections([
            { id: "sec-a", name: "Section A", type: "mcq", numQuestions: 10, marksPerQuestion: 1, totalMarks: 10 },
            { id: "sec-b", name: "Section B", type: "short_answer", numQuestions: 10, marksPerQuestion: 3, totalMarks: 30 },
            { id: "sec-c", name: "Section C", type: "long_answer", numQuestions: 8, marksPerQuestion: 5, totalMarks: 40 }
        ]);

        setTeacherInput(teacherMsg);

        // 3. Initiate Sequential Triggering
        setActiveAgentIndex(0);
    };

    return (
        <Button
            variant="outline"
            size="sm"
            onClick={handleDemo}
            disabled={status !== "idle"}
            className={cn(
                "w-full mb-6 border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                "h-9 text-[11px] font-black uppercase tracking-widest shadow-sm transition-all",
                "flex items-center justify-center gap-2 group"
            )}
        >
            <Sparkles className="h-3.5 w-3.5 text-amber-500 animate-pulse group-hover:scale-125 transition-transform" />
            AutoFill Demo
            <PlayCircle className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
        </Button>
    );
}
