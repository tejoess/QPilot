"use client";

/**
 * components/qpilot/AgentChatPanel.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Real-time chat log for orchestrated agent communication.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useEffect, useRef } from "react";
import { useQPilotStore, type ChatMessage } from "@/store/qpilotStore";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot, User, Loader2, Sparkles, BadgeCheck } from "lucide-react";
import { cn } from "@/lib/utils";

export function AgentChatPanel() {
    const { chatMessages, status } = useQPilotStore();
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [chatMessages]);

    return (
        <div className="flex flex-col h-full bg-slate-50/30 dark:bg-slate-950/20">
            <div className="px-6 py-4 bg-background border-b border-border/50 flex items-center justify-between sticky top-0 z-10">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-100 shadow-lg">
                        <Bot className="h-5 w-5" />
                    </div>
                    <div>
                        <h2 className="text-sm font-bold text-foreground leading-none mb-1">Orchestrator Control Log</h2>
                        <div className="flex flex-col gap-1">
                            <p className="text-[10px] text-muted-foreground uppercase font-medium tracking-wider">Active Multi-Agent Stream</p>
                            <div className="flex items-center gap-1.5">
                                {status === 'running' ? (
                                    <>
                                        <Sparkles className="h-2.5 w-2.5 animate-pulse text-amber-500" />
                                        <span className="text-[9px] text-primary/80 font-bold uppercase tracking-tight">Agents are actively synthesizing content...</span>
                                    </>
                                ) : status === 'completed' ? (
                                    <>
                                        <BadgeCheck className="h-2.5 w-2.5 text-green-500" />
                                        <span className="text-[9px] text-green-600 font-bold uppercase tracking-tight">Paper generation finalized.</span>
                                    </>
                                ) : (
                                    <span className="text-[9px] text-muted-foreground/60 font-bold uppercase tracking-tight italic">Waiting for pipeline start...</span>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                    <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-tighter">Live Monitor</span>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
                <div className="max-w-4xl mx-auto space-y-6">
                    {chatMessages.map((msg) => (
                        <div
                            key={msg.id}
                            className={cn(
                                "flex gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300",
                                msg.role === "teacher" ? "flex-row-reverse" : "flex-row"
                            )}
                        >
                            <div className={cn(
                                "h-9 w-9 rounded-xl flex items-center justify-center shrink-0 border shadow-sm",
                                msg.role === "teacher"
                                    ? "bg-primary text-primary-foreground border-primary/20"
                                    : msg.role === "orchestrator"
                                        ? "bg-slate-900 text-slate-100 border-slate-800"
                                        : "bg-background text-indigo-600 border-border/60"
                            )}>
                                {msg.role === "teacher" ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
                            </div>

                            <div className={cn(
                                "max-w-[85%] space-y-1.5",
                                msg.role === "teacher" ? "items-end" : "items-start"
                            )}>
                                <div className="flex items-center gap-2 px-1">
                                    <span className="text-[10px] font-black uppercase text-muted-foreground/80 tracking-widest">
                                        {msg.sender}
                                    </span>
                                    <span className="text-[9px] text-muted-foreground/40 font-bold">
                                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                    </span>
                                </div>
                                <div className={cn(
                                    "p-4 rounded-2xl text-xs leading-relaxed font-medium shadow-sm border transition-all hover:shadow-md",
                                    msg.role === "teacher"
                                        ? "bg-primary text-primary-foreground rounded-tr-none border-primary/20"
                                        : msg.role === "orchestrator"
                                            ? "bg-slate-900 text-slate-200 rounded-tl-none border-slate-800"
                                            : "bg-card rounded-tl-none border-border/80 text-foreground"
                                )}>
                                    {msg.content}
                                    {msg.role === "orchestrator" && msg.content.includes("...") && (
                                        <Loader2 className="h-3 w-3 animate-spin inline-block ml-3 opacity-50" />
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                    <div ref={scrollRef} className="h-4" />
                </div>
            </div>
        </div>
    );
}
