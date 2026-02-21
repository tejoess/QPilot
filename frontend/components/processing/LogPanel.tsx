"use client";

/**
 * components/processing/LogPanel.tsx
 */

import { useEffect, useRef } from "react";
import { Terminal, Copy } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useProcessingStore } from "@/store/processingStore";

export function LogPanel() {
    const logs = useProcessingStore((s) => s.logs);
    const viewportRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (viewportRef.current) {
            viewportRef.current.scrollTo({ top: viewportRef.current.scrollHeight, behavior: 'smooth' });
        }
    }, [logs]);

    const copyLogs = () => {
        navigator.clipboard.writeText(logs.join("\n"));
        toast.success("Logs copied to clipboard.");
    };

    return (
        <Card className="border-border/60 bg-slate-950 text-slate-300 overflow-hidden shadow-xl">
            <CardHeader className="py-3 px-4 border-b border-slate-800 flex flex-row items-center justify-between">
                <CardTitle className="text-xs font-mono flex items-center gap-2">
                    <Terminal className="h-4 w-4 text-emerald-500" />
                    Live Generation Logs
                </CardTitle>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-slate-500 hover:text-slate-300"
                    onClick={copyLogs}
                >
                    <Copy className="h-3 w-3" />
                </Button>
            </CardHeader>
            <CardContent className="p-0">
                <ScrollArea className="h-64 font-mono text-[11px] leading-relaxed">
                    <div ref={viewportRef} className="p-4 space-y-1">
                        {logs.length === 0 ? (
                            <p className="text-slate-600 italic">Waiting for connection...</p>
                        ) : (
                            logs.map((log, i) => {
                                const isError = log.toLowerCase().includes("error") || log.toLowerCase().includes("failed");
                                const isWarning = log.toLowerCase().includes("warning");

                                return (
                                    <div key={i} className="flex gap-3">
                                        <span className="text-slate-700 select-none">[{i + 1}]</span>
                                        <span className={isError ? "text-red-400" : isWarning ? "text-amber-400" : "text-slate-300"}>
                                            {log}
                                        </span>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    );
}
