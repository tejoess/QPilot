/**
 * components/dashboard/FloatingOrchestrator.tsx
 */

import { useState } from "react";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import {
    Bot,
    Sparkles,
    PlusCircle,
    History,
    BarChart3,
    Loader2,
    Send
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useDashboardStore } from "@/store/dashboardStore";
import { cn } from "@/lib/utils";

export function FloatingOrchestrator() {
    const router = useRouter();
    const { orchestratorOpen, setOrchestratorOpen } = useDashboardStore();
    const [isRedirecting, setIsRedirecting] = useState<string | null>(null);

    const handleAction = (label: string, route: string) => {
        setIsRedirecting(label);

        // Controlled delay for the guided orchestration feel
        setTimeout(() => {
            setIsRedirecting(null);
            setOrchestratorOpen(false);
            router.push(route);
        }, 1500);
    };

    const QUICK_ACTIONS = [
        { label: "Create full question paper", route: "/qpilot", icon: PlusCircle },
        { label: "Generate from PYQs", route: "/qpilot?source=pyq", icon: History },
        { label: "Create interview", route: "/interview", icon: Sparkles, disabled: true },
        { label: "View analytics", route: "/analytics", icon: BarChart3 },
    ];

    return (
        <div className="fixed bottom-8 right-8 z-50">
            <Sheet open={orchestratorOpen} onOpenChange={setOrchestratorOpen}>
                <SheetTrigger asChild>
                    <Button
                        size="icon"
                        className="h-16 w-16 rounded-full shadow-2xl shadow-primary/40 flex items-center justify-center bg-primary hover:bg-primary/90 transition-all active:scale-90 border-4 border-background"
                    >
                        <Bot className="h-8 w-8 text-primary-foreground animate-in zoom-in duration-500" />
                    </Button>
                </SheetTrigger>
                <SheetContent side="right" className="w-[400px] sm:w-[500px] border-l border-border/40 bg-card p-0 overflow-hidden flex flex-col">
                    <SheetHeader className="p-6 bg-primary/5 border-bottom border-border/10">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-primary text-primary-foreground">
                                <Bot className="h-5 w-5" />
                            </div>
                            <SheetTitle className="text-lg font-black tracking-tight">QPilot Assistant</SheetTitle>
                        </div>
                    </SheetHeader>

                    <div className="flex-1 p-8 space-y-8 overflow-y-auto">
                        {/* Chat Bubble */}
                        <div className="flex gap-4 animate-in slide-in-from-left-4 duration-500">
                            <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center shrink-0 border border-border/20">
                                <Bot className="h-5 w-5 text-muted-foreground" />
                            </div>
                            <div className="bg-muted/50 p-5 rounded-2xl rounded-tl-none border border-border/20 shadow-sm max-w-[85%]">
                                <p className="text-sm font-medium leading-relaxed text-foreground">
                                    Hi, I&apos;m <span className="font-black text-primary">QPilot</span>. How can I help you generate your question paper today?
                                </p>
                            </div>
                        </div>

                        {/* Guidance Steps */}
                        <div className="space-y-4 pt-4">
                            <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 px-1">Select an objective</span>
                            <div className="grid grid-cols-1 gap-3">
                                {QUICK_ACTIONS.map((action, idx) => (
                                    <Button
                                        key={idx}
                                        variant="outline"
                                        disabled={action.disabled || isRedirecting !== null}
                                        onClick={() => handleAction(action.label, action.route)}
                                        className={cn(
                                            "h-16 justify-between px-5 font-bold text-sm tracking-tight border-border/40 hover:bg-primary/5 hover:border-primary/20 hover:text-primary transition-all group",
                                            isRedirecting === action.label && "bg-primary/10 border-primary text-primary"
                                        )}
                                    >
                                        <div className="flex items-center gap-4">
                                            <action.icon className="h-5 w-5 text-muted-foreground/60 group-hover:text-primary transition-colors" />
                                            <span>{action.label}</span>
                                        </div>
                                        {isRedirecting === action.label ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <Send className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-all translate-x-[-10px] group-hover:translate-x-0" />
                                        )}
                                    </Button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="p-6 border-t border-border/20 bg-muted/20">
                        <div className="text-[10px] font-bold text-muted-foreground/60 text-center uppercase tracking-widest">
                            AI Orchestration in Progress
                        </div>
                    </div>
                </SheetContent>
            </Sheet>
        </div>
    );
}
